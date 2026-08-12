"""
Solidarity Financing — native Erdpuls router, v0.8
==================================================
Project: Solidarity Financing 2026 (working title) — Michel Garand
Mounted at /erdpuls-verkhovyna/solidarity inside the Erdpuls dashboard.
Origin: ported 2026-08-10 from the standalone Flask prototype
(app.py v0.2) into Erdpuls conventions: FastAPI router, Erdpuls
session-cookie auth (app.auth), Erdpuls RBAC (app.roles — facilitator
and above), raw SQL against the dedicated `solidarity` schema created
by db/scripts/012_solidarity_financing.sql. No Erdpuls table is touched.

Access: every route requires an Erdpuls login with role facilitator or
higher (has_role_or_higher). The module is deliberately NOT linked from
the public initiative page — internal until the hosts' yes.

Invariants (unchanged from the paper layer):
  - No child data anywhere. - Round screens and reports: sums only.
  - Every amount carries a status; DB enum refuses untagged figures.
  - Currency UAH; EUR only as a stated-rate note.
  - Records and computes; moves no money.

Changelog:
  v0.8 (August 2026) — sessions are created ONLY by ticking solidarity
      financing when an offering is created. The module's own "new
      session" form is gone and its endpoint refuses, so an offering is
      the single source of truth for what a session is: a session now
      always has a thing it finances, a description, an organiser and
      deadlines, rather than a bare label someone typed. Sessions whose
      offering is later deleted survive unlinked — a settlement account
      must outlive the listing — but no new session can begin that way.
  v0.7 (August 2026) — a session may be linked to an Erdpuls offering
      (migration 014), chosen at offering creation by a facilitator.
      The link carries words, not money: offering costs are EUR, the
      session budget is UAH, and nothing is converted. The threshold
      model's contributions and the round's pledges stay separate
      ledgers that never reconcile per person — the first records who
      gave what, the second is anonymous by design.
  v0.6 (August 2026) — entry points from the dashboard for facilitator
      and above; the role gate is unchanged and still decides access.
  v0.5 (August 2026) — session description: what the session offers, in
      plain words, shown above the open budget so a family reads the
      thing and its cost together. Editable at any time (it is not a
      figure). Requires migration 013.
      Round deletion: a round with NO pledges can be deleted, which
      unfreezes the budget — nobody has committed against those figures
      yet, so nothing is broken by removing it. The moment one pledge
      exists the round is permanent and the freeze absolute. The frozen
      notice now states which of the two cases holds rather than
      claiming pledges that may not exist.
  v0.4 (August 2026) — budget lines editable and deletable, but ONLY
      while the session has no bidding round. Once the first round is
      opened the budget is frozen: the figure families pledged against
      cannot be rewritten behind them. Frozen sessions expose no edit
      or delete control, and the POST endpoints refuse independently
      of the UI (the lock is server-side, not a hidden button).
      Corrections after a round belong in the settlement account.
  v0.3 (August 2026) — native Erdpuls port.
  v0.2 — prefix-safe Flask standalone.  v0.1 — Flask standalone.

Integration (two lines in app/main.py):
  from .routers.solidarity import router as solidarity_router
  app.include_router(solidarity_router)
"""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from ..models import User
from ..roles import has_role_or_higher

PREFIX = "/erdpuls-verkhovyna/solidarity"
VALID_STATUSES = ("estimate", "budget", "pledge", "settled")

router = APIRouter(prefix=PREFIX, tags=["solidarity"])
templates = Jinja2Templates(directory="templates")


# ── access: facilitator or higher, via Erdpuls RBAC ──────────

def require_facilitator(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not has_role_or_higher(user.role, "facilitator"):
        raise HTTPException(status_code=403,
                            detail="Solidarity financing requires the facilitator role.")
    return user


# ── helpers ──────────────────────────────────────────────────

def parse_amount(raw: str) -> Decimal:
    try:
        amt = Decimal(str(raw).strip().replace(" ", ""))
    except InvalidOperation:
        raise ValueError(f"'{raw}' is not an amount")
    if amt < 0:
        raise ValueError("negative amount")
    return amt


def need_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES} — refusing to guess")
    return s


def render(name: str, request: Request, user: User, **ctx):
    ctx.update({"request": request, "user": user, "prefix": PREFIX,
                "statuses": VALID_STATUSES})
    return templates.TemplateResponse(f"solidarity/{name}", ctx)


def back(request: Request, path: str, error: str = "") -> RedirectResponse:
    url = PREFIX + path + (f"?error={error}" if error else "")
    return RedirectResponse(url=url, status_code=303)


def rows(db: Session, sql: str, **params):
    return db.execute(text(sql), params).mappings().all()


def one(db: Session, sql: str, **params):
    return db.execute(text(sql), params).mappings().first()


def budget_locked(db: Session, sid: int) -> bool:
    """True once any bidding round exists for this session.

    The open budget is what the families pledge against. Editing a line
    after a round has run would silently change the remainder the room
    agreed to close, so the budget freezes when the first round opens.
    Corrections from that point are recorded in the settlement account,
    where they stay visible, rather than overwritten here.
    """
    return one(db, """SELECT 1 FROM solidarity.bidding_round
                      WHERE session_id = :i LIMIT 1""", i=sid) is not None


def session_pledge_count(db: Session, sid: int) -> int:
    """How many pledges exist across all rounds of this session.

    Zero means the freeze is precautionary — a round is open but nobody
    has committed anything, so the round may still be deleted. Above
    zero the freeze is permanent: families have pledged against these
    figures and the figures must not move behind them.
    """
    r = one(db, """SELECT COUNT(p.id) AS n FROM solidarity.pledge p
                   JOIN solidarity.bidding_round br ON br.id = p.round_id
                   WHERE br.session_id = :i""", i=sid)
    return int(r["n"]) if r else 0


LOCK_MESSAGE = ("The budget is frozen: a bidding round is open for this session. "
                "Delete the round to edit the budget, or record the correction in "
                "the settlement account.")

LOCK_MESSAGE_PLEDGED = ("The budget is frozen: families have pledged against these "
                        "figures. They cannot be edited. Record any correction in "
                        "the settlement account instead.")


def lock_message(db: Session, sid: int) -> str:
    return LOCK_MESSAGE_PLEDGED if session_pledge_count(db, sid) else LOCK_MESSAGE


# ── sessions + budget ────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: User = Depends(require_facilitator),
          db: Session = Depends(get_db)):
    sess = rows(db, """SELECT s.*, vb.cost_uah, vb.cover_uah, vb.remainder_uah
                       FROM solidarity.camp_session s
                       JOIN solidarity.v_session_budget vb ON vb.session_id = s.id
                       ORDER BY s.id""")
    return render("index.html", request, user, sessions=sess,
                  error=request.query_params.get("error", ""))


@router.post("/")
def create_session_refused(request: Request,
                           user: User = Depends(require_facilitator)):
    """Sessions are not created here.

    A session exists to finance something. Creating one from a bare label
    would leave it without the description, organiser and deadlines that
    make it answerable, so the only door is the offering form: tick
    solidarity financing there and the linked session opens with it.
    """
    return back(request, "/",
                "Sessions are created by ticking solidarity financing when an offering "
                "is created. Open the offering form to start one.")


@router.get("/session/{sid}", response_class=HTMLResponse)
def session_view(sid: int, request: Request,
                 user: User = Depends(require_facilitator),
                 db: Session = Depends(get_db)):
    s = one(db, "SELECT * FROM solidarity.camp_session WHERE id = :i", i=sid)
    if not s:
        raise HTTPException(404)
    offering = None
    if s["offering_id"]:
        offering = one(db, """SELECT id, title, threshold_amount
                              FROM erdpuls_threshold.offerings WHERE id = :o""",
                       o=s["offering_id"])
    return render("session.html", request, user, s=s, offering=offering,
        lines=rows(db, """SELECT * FROM solidarity.budget_line WHERE session_id = :i
                          ORDER BY is_transfer_in, id""", i=sid),
        vb=one(db, "SELECT * FROM solidarity.v_session_budget WHERE session_id = :i", i=sid),
        rounds=rows(db, """SELECT * FROM solidarity.v_round_totals WHERE session_id = :i
                           ORDER BY round_no""", i=sid),
        stl=one(db, "SELECT * FROM solidarity.settlement WHERE session_id = :i", i=sid),
        locked=budget_locked(db, sid),
        pledges_exist=session_pledge_count(db, sid) > 0,
        error=request.query_params.get("error", ""))


@router.post("/session/{sid}/budget")
def add_budget_line(sid: int, request: Request, line_item: str = Form(...),
                    amount_uah: str = Form(...), status: str = Form(""),
                    is_transfer_in: str = Form(""), note: str = Form(""),
                    user: User = Depends(require_facilitator),
                    db: Session = Depends(get_db)):
    if budget_locked(db, sid):
        return back(request, f"/session/{sid}", lock_message(db, sid))
    try:
        db.execute(text("""INSERT INTO solidarity.budget_line
                           (session_id, line_item, amount_uah, status, is_transfer_in, note)
                           VALUES (:s, :li, :a, :st, :ti, :n)"""),
                   {"s": sid, "li": line_item.strip(), "a": parse_amount(amount_uah),
                    "st": need_status(status), "ti": bool(is_transfer_in), "n": note})
        db.commit()
    except ValueError as e:
        return back(request, f"/session/{sid}", str(e))
    return back(request, f"/session/{sid}")


@router.post("/session/{sid}/budget/{lid}/edit")
def edit_budget_line(sid: int, lid: int, request: Request,
                     line_item: str = Form(...), amount_uah: str = Form(...),
                     status: str = Form(""), is_transfer_in: str = Form(""),
                     note: str = Form(""),
                     user: User = Depends(require_facilitator),
                     db: Session = Depends(get_db)):
    """Edit one budget line. Refused once a round exists for the session."""
    if budget_locked(db, sid):
        return back(request, f"/session/{sid}", lock_message(db, sid))
    line = one(db, """SELECT id FROM solidarity.budget_line
                      WHERE id = :l AND session_id = :s""", l=lid, s=sid)
    if not line:
        raise HTTPException(404)
    try:
        db.execute(text("""UPDATE solidarity.budget_line
                           SET line_item = :li, amount_uah = :a, status = :st,
                               is_transfer_in = :ti, note = :n
                           WHERE id = :l AND session_id = :s"""),
                   {"li": line_item.strip(), "a": parse_amount(amount_uah),
                    "st": need_status(status), "ti": bool(is_transfer_in),
                    "n": note, "l": lid, "s": sid})
        db.commit()
    except ValueError as e:
        db.rollback()
        return back(request, f"/session/{sid}", str(e))
    return back(request, f"/session/{sid}")


@router.post("/session/{sid}/budget/{lid}/delete")
def delete_budget_line(sid: int, lid: int, request: Request,
                       user: User = Depends(require_facilitator),
                       db: Session = Depends(get_db)):
    """Delete one budget line. Refused once a round exists for the session."""
    if budget_locked(db, sid):
        return back(request, f"/session/{sid}", lock_message(db, sid))
    db.execute(text("""DELETE FROM solidarity.budget_line
                       WHERE id = :l AND session_id = :s"""), {"l": lid, "s": sid})
    db.commit()
    return back(request, f"/session/{sid}")


@router.post("/session/{sid}/details")
def edit_session_details(sid: int, request: Request, label: str = Form(...),
                         days: str = Form(""), adopted_on: str = Form(""),
                         description: str = Form(""),
                         user: User = Depends(require_facilitator),
                         db: Session = Depends(get_db)):
    """Edit the session label, length, adoption date and description.

    Not subject to the budget freeze: the description is not a figure.
    What the session offers may need clarifying at any point, and doing
    so changes nothing anyone pledged against.
    """
    s = one(db, "SELECT id FROM solidarity.camp_session WHERE id = :i", i=sid)
    if not s:
        raise HTTPException(404)
    clash = one(db, """SELECT 1 FROM solidarity.camp_session
                       WHERE label = :l AND id <> :i""", l=label.strip(), i=sid)
    if clash:
        return back(request, f"/session/{sid}", "another session already has that label")
    try:
        db.execute(text("""UPDATE solidarity.camp_session
                           SET label = :l, days = :d, adopted_on = :a, description = :desc
                           WHERE id = :i"""),
                   {"l": label.strip(), "d": int(days) if days.strip() else None,
                    "a": adopted_on or None, "desc": description.strip(), "i": sid})
        db.commit()
    except ValueError:
        db.rollback()
        return back(request, f"/session/{sid}", "days must be a whole number")
    return back(request, f"/session/{sid}")


@router.post("/round/{rid}/delete")
def delete_round(rid: int, request: Request,
                 user: User = Depends(require_facilitator),
                 db: Session = Depends(get_db)):
    """Delete a round that holds no pledges, unfreezing the budget.

    Permitted only while the round is empty. An empty round has asked
    nothing of anyone: no family has committed against the figures, so
    removing it breaks no promise and the budget may be corrected. Once
    a single pledge exists the round is permanent — deleting it would
    erase what a family committed and quietly move the figure they
    committed against.
    """
    r = one(db, "SELECT * FROM solidarity.bidding_round WHERE id = :i", i=rid)
    if not r:
        raise HTTPException(404)
    sid = r["session_id"]
    n = one(db, "SELECT COUNT(*) AS n FROM solidarity.pledge WHERE round_id = :i", i=rid)
    if int(n["n"]) > 0:
        return back(request, f"/session/{sid}",
                    "This round holds pledges and cannot be deleted. Families have "
                    "committed against these figures; record any correction in the "
                    "settlement account.")
    db.execute(text("DELETE FROM solidarity.bidding_round WHERE id = :i"), {"i": rid})
    db.commit()
    return back(request, f"/session/{sid}")


@router.post("/session/{sid}/new-round")
def new_round(sid: int, user: User = Depends(require_facilitator),
              db: Session = Depends(get_db)):
    db.execute(text("""INSERT INTO solidarity.bidding_round (session_id, round_no, held_on)
                       SELECT :s, COALESCE(MAX(round_no), 0) + 1, CURRENT_DATE
                       FROM solidarity.bidding_round WHERE session_id = :s"""), {"s": sid})
    db.commit()
    return RedirectResponse(url=f"{PREFIX}/session/{sid}", status_code=303)


# ── tokens (mapping optional — may stay on paper) ────────────

@router.get("/session/{sid}/tokens", response_class=HTMLResponse)
def tokens(sid: int, request: Request, user: User = Depends(require_facilitator),
           db: Session = Depends(get_db)):
    s = one(db, "SELECT * FROM solidarity.camp_session WHERE id = :i", i=sid)
    if not s:
        raise HTTPException(404)
    toks = rows(db, """SELECT rt.token,
                       CASE WHEN tm.token_id IS NULL THEN 'on paper' ELSE 'in registry' END AS mapping
                       FROM solidarity.round_token rt
                       LEFT JOIN solidarity.token_mapping tm ON tm.token_id = rt.id
                       WHERE rt.session_id = :i ORDER BY rt.token""", i=sid)
    return render("tokens.html", request, user, s=s, toks=toks,
                  error=request.query_params.get("error", ""))


@router.post("/session/{sid}/tokens")
def add_token(sid: int, request: Request, token: str = Form(...),
              household: str = Form(""),
              user: User = Depends(require_facilitator),
              db: Session = Depends(get_db)):
    db.execute(text("""INSERT INTO solidarity.round_token (session_id, token)
                       VALUES (:s, :t) ON CONFLICT DO NOTHING"""),
               {"s": sid, "t": token.strip()})
    if household.strip():
        db.execute(text("""WITH h AS (INSERT INTO solidarity.household (display_name)
                                      VALUES (:hh) RETURNING id),
                                t AS (SELECT id FROM solidarity.round_token
                                      WHERE session_id = :s AND token = :t)
                           INSERT INTO solidarity.token_mapping (token_id, household_id)
                           SELECT t.id, h.id FROM t, h ON CONFLICT DO NOTHING"""),
                   {"hh": household.strip(), "s": sid, "t": token.strip()})
    db.commit()
    return back(request, f"/session/{sid}/tokens")


# ── rounds + pledges (sums only on screen) ───────────────────

@router.get("/round/{rid}", response_class=HTMLResponse)
def round_view(rid: int, request: Request,
               user: User = Depends(require_facilitator),
               db: Session = Depends(get_db)):
    r = one(db, """SELECT br.*, cs.label FROM solidarity.bidding_round br
                   JOIN solidarity.camp_session cs ON cs.id = br.session_id
                   WHERE br.id = :i""", i=rid)
    if not r:
        raise HTTPException(404)
    vt = one(db, "SELECT * FROM solidarity.v_round_totals WHERE round_id = :i", i=rid)
    return render("round.html", request, user, r=r, vt=vt,
                  error=request.query_params.get("error", ""))


@router.post("/round/{rid}/pledge")
def enter_pledge(rid: int, request: Request, token: str = Form(...),
                 amount_uah: str = Form(...),
                 user: User = Depends(require_facilitator),
                 db: Session = Depends(get_db)):
    r = one(db, "SELECT * FROM solidarity.bidding_round WHERE id = :i", i=rid)
    if not r or r["state"] != "open":
        return back(request, f"/round/{rid}", "round is not open")
    tok = one(db, """SELECT id FROM solidarity.round_token
                     WHERE session_id = :s AND token = :t""",
              s=r["session_id"], t=token.strip())
    if not tok:
        return back(request, f"/round/{rid}",
                    "unknown token for this session — add it on the tokens page first")
    try:
        db.execute(text("""INSERT INTO solidarity.pledge (round_id, token_id, amount_uah)
                           VALUES (:r, :t, :a)
                           ON CONFLICT (round_id, token_id)
                           DO UPDATE SET amount_uah = EXCLUDED.amount_uah"""),
                   {"r": rid, "t": tok["id"], "a": parse_amount(amount_uah)})
        db.commit()
    except ValueError as e:
        return back(request, f"/round/{rid}", str(e))
    return back(request, f"/round/{rid}")


@router.post("/round/{rid}/state")
def round_state(rid: int, request: Request, action: str = Form(...),
                user: User = Depends(require_facilitator),
                db: Session = Depends(get_db)):
    if action not in ("close", "stop"):
        raise HTTPException(400)
    db.execute(text("UPDATE solidarity.bidding_round SET state = :st WHERE id = :i"),
               {"st": "closed" if action == "close" else "stopped", "i": rid})
    db.commit()
    return back(request, f"/round/{rid}")


# ── supporter circle ─────────────────────────────────────────

@router.get("/supporters", response_class=HTMLResponse)
def supporters(request: Request, user: User = Depends(require_facilitator),
               db: Session = Depends(get_db)):
    return render("supporters.html", request, user,
        sups=rows(db, """SELECT s.token, s.display_name, COUNT(c.id) AS n,
                                COALESCE(SUM(c.amount_uah), 0) AS total
                         FROM solidarity.supporter s
                         LEFT JOIN solidarity.contribution c ON c.supporter_id = s.id
                         GROUP BY s.id ORDER BY s.token"""),
        periods=rows(db, "SELECT * FROM solidarity.v_period_summary ORDER BY period DESC"),
        error=request.query_params.get("error", ""))


@router.post("/supporters")
def add_supporter(request: Request, token: str = Form(...),
                  display_name: str = Form(""), note: str = Form(""),
                  user: User = Depends(require_facilitator),
                  db: Session = Depends(get_db)):
    exists = one(db, "SELECT 1 FROM solidarity.supporter WHERE token = :t", t=token.strip())
    if exists:
        return back(request, "/supporters", "supporter token already exists")
    db.execute(text("""INSERT INTO solidarity.supporter (token, display_name, note)
                       VALUES (:t, :d, :n)"""),
               {"t": token.strip(), "d": display_name.strip() or None, "n": note})
    db.commit()
    return back(request, "/supporters")


@router.post("/supporters/contribution")
def add_contribution(request: Request, token: str = Form(...), period: str = Form(...),
                     amount_uah: str = Form(...), status: str = Form(""),
                     note: str = Form(""),
                     user: User = Depends(require_facilitator),
                     db: Session = Depends(get_db)):
    sup = one(db, "SELECT id FROM solidarity.supporter WHERE token = :t", t=token.strip())
    if not sup:
        return back(request, "/supporters", "unknown supporter token — add the supporter first")
    try:
        db.execute(text("""INSERT INTO solidarity.contribution
                           (supporter_id, period, amount_uah, status, note)
                           VALUES (:s, :p, :a, :st, :n)"""),
                   {"s": sup["id"], "p": period.strip(), "a": parse_amount(amount_uah),
                    "st": need_status(status), "n": note})
        db.commit()
    except ValueError as e:
        db.rollback()
        return back(request, "/supporters", str(e))
    except Exception:
        db.rollback()
        return back(request, "/supporters", "period must be YYYY-MM")
    return back(request, "/supporters")


# ── settlement + report ──────────────────────────────────────

@router.get("/session/{sid}/settlement", response_class=HTMLResponse)
def settlement_view(sid: int, request: Request,
                    user: User = Depends(require_facilitator),
                    db: Session = Depends(get_db)):
    s = one(db, "SELECT * FROM solidarity.camp_session WHERE id = :i", i=sid)
    if not s:
        raise HTTPException(404)
    stl = one(db, "SELECT * FROM solidarity.settlement WHERE session_id = :i", i=sid)
    return render("settlement.html", request, user, s=s, stl=stl,
                  error=request.query_params.get("error", ""))


@router.post("/session/{sid}/settlement")
def settlement_save(sid: int, request: Request,
                    received_uah: str = Form(...), outstanding_uah: str = Form(...),
                    spent_uah: str = Form(...), to_infrastructure_uah: str = Form(...),
                    carried_by_hosts_uah: str = Form(...), note: str = Form(""),
                    user: User = Depends(require_facilitator),
                    db: Session = Depends(get_db)):
    try:
        vals = {k: parse_amount(v) for k, v in [
            ("r", received_uah), ("o", outstanding_uah), ("sp", spent_uah),
            ("ti", to_infrastructure_uah), ("ch", carried_by_hosts_uah)]}
    except ValueError as e:
        return back(request, f"/session/{sid}/settlement", str(e))
    db.execute(text("""INSERT INTO solidarity.settlement
        (session_id, received_uah, outstanding_uah, spent_uah,
         to_infrastructure_uah, carried_by_hosts_uah, note)
        VALUES (:sid, :r, :o, :sp, :ti, :ch, :n)
        ON CONFLICT (session_id) DO UPDATE SET
          received_uah = EXCLUDED.received_uah,
          outstanding_uah = EXCLUDED.outstanding_uah,
          spent_uah = EXCLUDED.spent_uah,
          to_infrastructure_uah = EXCLUDED.to_infrastructure_uah,
          carried_by_hosts_uah = EXCLUDED.carried_by_hosts_uah,
          note = EXCLUDED.note, drawn_up_on = CURRENT_DATE"""),
               {"sid": sid, "n": note, **vals})
    db.commit()
    return back(request, f"/session/{sid}/settlement")


@router.get("/report/{sid}", response_class=HTMLResponse)
def report(sid: int, request: Request, user: User = Depends(require_facilitator),
           db: Session = Depends(get_db)):
    vb = one(db, "SELECT * FROM solidarity.v_session_budget WHERE session_id = :i", i=sid)
    if not vb:
        raise HTTPException(404)
    return render("report.html", request, user, vb=vb,
        rounds=rows(db, """SELECT * FROM solidarity.v_round_totals
                           WHERE session_id = :i ORDER BY round_no""", i=sid),
        periods=rows(db, "SELECT * FROM solidarity.v_period_summary ORDER BY period"))
