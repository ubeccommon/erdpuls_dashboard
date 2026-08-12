"""
Solidarity Financing — native Erdpuls router, v1.1
==================================================
Project: Solidarity Financing 2026 (working title) — Michel Garand
Mounted per initiative at /{initiative-slug}/solidarity inside the
Erdpuls dashboard, e.g. /erdpuls-verkhovyna/solidarity.
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
  v1.1 (August 2026) — access is now place-bound. Opening an initiative's
      financing needs the global facilitator role AND membership of that
      initiative at facilitator level or above. A facilitator elsewhere
      gets 403, not a readable page. Platform admins and moderators keep
      global oversight without holding a membership everywhere.
      Requires migration 018.
  v1.0 (August 2026) — solidarity becomes per-initiative. The mount path
      is no longer hardcoded to one place: routes live under
      /{initiative_slug}/solidarity, sessions belong to an initiative,
      and each initiative sees only its own. A session inherits its place
      from the offering that opened it and keeps it directly, so the
      record survives that offering's deletion. An unknown or unpublished
      slug is a 404 rather than an empty module.
      Requires migration 017.
  v0.9 (August 2026) — a session can be deleted, on the same terms as a
      round: only while nothing has been committed against it. No pledge
      and no settlement means nobody promised anything and no account was
      drawn, so removing it erases no record. One pledge or a drawn-up
      settlement makes it permanent — a financing record must not vanish
      once families have committed or the cycle has been accounted for.
      Deleting a session leaves its offering standing; the offering is
      simply no longer financed this way.
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
from ..membership import member_at_least, has_global_oversight

VALID_STATUSES = ("estimate", "budget", "pledge", "settled")

# The module mounts under each initiative rather than one hardcoded place:
# /{initiative_slug}/solidarity. Routes are registered before the
# catch-all /{slug} initiative page, which they cannot shadow because
# they are two segments deep.
router = APIRouter(prefix="/{initiative_slug}/solidarity", tags=["solidarity"])

# A second, prefix-free router for the chooser at /solidarity. It lists the
# initiatives a facilitator can open the module for, so navigation links do
# not have to guess a slug. Registered before the catch-all /{slug}.
chooser = APIRouter(tags=["solidarity"])


def prefix_for(slug: str) -> str:
    return f"/{slug}/solidarity"
templates = Jinja2Templates(directory="templates")


# ── access: facilitator or higher, via Erdpuls RBAC ──────────

def require_facilitator(request: Request, db: Session = Depends(get_db)) -> User:
    """Global gate: may this person run financing anywhere at all?

    Place-bound access is decided separately by require_member below,
    because the two questions are different: what a person may do, and
    where they may do it.
    """
    user = get_current_user(request, db)
    if not has_role_or_higher(user.role, "facilitator"):
        raise HTTPException(status_code=403,
                            detail="Solidarity financing requires the facilitator role.")
    return user


def require_member(initiative_slug: str, request: Request,
                   db: Session = Depends(get_db)):
    """Place-bound gate: may this person run financing HERE?

    Needs the global facilitator role and membership of this initiative
    at facilitator level or above. Platform admins and moderators pass
    without a membership row, since their oversight is not place-bound.
    Returns the initiative, so handlers depend on this alone.
    """
    user = require_facilitator(request, db)
    init = one(db, """SELECT id, slug, name, location FROM erdpuls_threshold.initiatives
                      WHERE slug = :s""", s=initiative_slug)
    if not init:
        raise HTTPException(status_code=404, detail="No such initiative.")
    if not member_at_least(db, user, init["id"], "facilitator"):
        raise HTTPException(
            status_code=403,
            detail=("You are not a facilitator of this initiative. Financing is "
                    "run by the people of the place it belongs to."))
    return init


def resolve_initiative(init=Depends(require_member)):
    """Resolve the initiative, having checked the caller belongs to it.

    An unknown slug is a 404, not an empty module: a financing page for a
    place that does not exist would invite entering figures nobody could
    ever account for. A known slug the caller does not belong to is a
    403, for the same reason in reverse.
    """
    return init



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


def render(name: str, request: Request, user: User, initiative, **ctx):
    ctx.update({"request": request, "user": user, "initiative": initiative,
                "prefix": prefix_for(initiative["slug"]),
                "statuses": VALID_STATUSES})
    return templates.TemplateResponse(f"solidarity/{name}", ctx)


def back(slug: str, path: str, error: str = "") -> RedirectResponse:
    url = prefix_for(slug) + path + (f"?error={error}" if error else "")
    return RedirectResponse(url=url, status_code=303)


def rows(db: Session, sql: str, **params):
    return db.execute(text(sql), params).mappings().all()


def one(db: Session, sql: str, **params):
    return db.execute(text(sql), params).mappings().first()


def session_of(db: Session, sid: int, init):
    """Fetch a session, but only if it belongs to this initiative.

    Scoping every lookup by initiative is what keeps one place's figures
    out of another's screens: a session id from elsewhere is a 404 here,
    not a readable page.
    """
    s = one(db, """SELECT * FROM solidarity.camp_session
                   WHERE id = :i AND initiative_id = :n""", i=sid, n=init["id"])
    if not s:
        raise HTTPException(404)
    return s


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


def session_delete_block(db: Session, sid: int) -> str:
    """Return the reason a session may not be deleted, or "" if it may.

    A session may go only while nothing has been committed against it.
    Pledges are promises families made; a settlement is the account of a
    cycle that happened. Either one makes the session a record, and
    records are not deleted — they are superseded, corrected in the
    settlement account, or left standing.
    """
    if session_pledge_count(db, sid):
        return ("This session holds pledges. Families have committed against its "
                "figures, so it cannot be deleted — a financing record stays.")
    if one(db, "SELECT 1 FROM solidarity.settlement WHERE session_id = :i", i=sid):
        return ("This session has a settlement account. The cycle has been accounted "
                "for, so it cannot be deleted.")
    return ""


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
          init=Depends(resolve_initiative),
          db: Session = Depends(get_db)):
    sess = rows(db, """SELECT s.*, vb.cost_uah, vb.cover_uah, vb.remainder_uah
                       FROM solidarity.camp_session s
                       JOIN solidarity.v_session_budget vb ON vb.session_id = s.id
                       WHERE s.initiative_id = :i
                       ORDER BY s.id""", i=init["id"])
    return render("index.html", request, user, init, sessions=sess,
                  error=request.query_params.get("error", ""))


@router.post("/")
def create_session_refused(request: Request,
                           user: User = Depends(require_facilitator),
                           init=Depends(resolve_initiative)):
    """Sessions are not created here.

    A session exists to finance something. Creating one from a bare label
    would leave it without the description, organiser and deadlines that
    make it answerable, so the only door is the offering form: tick
    solidarity financing there and the linked session opens with it.
    """
    return back(init["slug"], "/",
                "Sessions are created by ticking solidarity financing when an offering "
                "is created. Open the offering form to start one.")


@router.get("/session/{sid}", response_class=HTMLResponse)
def session_view(sid: int, request: Request,
                 user: User = Depends(require_facilitator),
                 init=Depends(resolve_initiative),
                 db: Session = Depends(get_db)):
    s = session_of(db, sid, init)
    offering = None
    if s["offering_id"]:
        offering = one(db, """SELECT id, title, threshold_amount
                              FROM erdpuls_threshold.offerings WHERE id = :o""",
                       o=s["offering_id"])
    return render("session.html", request, user, init, s=s, offering=offering,
        lines=rows(db, """SELECT * FROM solidarity.budget_line WHERE session_id = :i
                          ORDER BY is_transfer_in, id""", i=sid),
        vb=one(db, "SELECT * FROM solidarity.v_session_budget WHERE session_id = :i", i=sid),
        rounds=rows(db, """SELECT * FROM solidarity.v_round_totals WHERE session_id = :i
                           ORDER BY round_no""", i=sid),
        stl=one(db, "SELECT * FROM solidarity.settlement WHERE session_id = :i", i=sid),
        locked=budget_locked(db, sid),
        pledges_exist=session_pledge_count(db, sid) > 0,
        delete_block=session_delete_block(db, sid),
        error=request.query_params.get("error", ""))


@router.post("/session/{sid}/budget")
def add_budget_line(sid: int, request: Request, line_item: str = Form(...),
                    amount_uah: str = Form(...), status: str = Form(""),
                    is_transfer_in: str = Form(""), note: str = Form(""),
                    user: User = Depends(require_facilitator),
                    init=Depends(resolve_initiative),
                    db: Session = Depends(get_db)):
    session_of(db, sid, init)
    if budget_locked(db, sid):
        return back(init["slug"], f"/session/{sid}", lock_message(db, sid))
    try:
        db.execute(text("""INSERT INTO solidarity.budget_line
                           (session_id, line_item, amount_uah, status, is_transfer_in, note)
                           VALUES (:s, :li, :a, :st, :ti, :n)"""),
                   {"s": sid, "li": line_item.strip(), "a": parse_amount(amount_uah),
                    "st": need_status(status), "ti": bool(is_transfer_in), "n": note})
        db.commit()
    except ValueError as e:
        return back(init["slug"], f"/session/{sid}", str(e))
    return back(init["slug"], f"/session/{sid}")


@router.post("/session/{sid}/budget/{lid}/edit")
def edit_budget_line(sid: int, lid: int, request: Request,
                     line_item: str = Form(...), amount_uah: str = Form(...),
                     status: str = Form(""), is_transfer_in: str = Form(""),
                     note: str = Form(""),
                     user: User = Depends(require_facilitator),
                     init=Depends(resolve_initiative),
                     db: Session = Depends(get_db)):
    """Edit one budget line. Refused once a round exists for the session."""
    session_of(db, sid, init)
    if budget_locked(db, sid):
        return back(init["slug"], f"/session/{sid}", lock_message(db, sid))
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
        return back(init["slug"], f"/session/{sid}", str(e))
    return back(init["slug"], f"/session/{sid}")


@router.post("/session/{sid}/budget/{lid}/delete")
def delete_budget_line(sid: int, lid: int, request: Request,
                       user: User = Depends(require_facilitator),
                       init=Depends(resolve_initiative),
                       db: Session = Depends(get_db)):
    """Delete one budget line. Refused once a round exists for the session."""
    session_of(db, sid, init)
    if budget_locked(db, sid):
        return back(init["slug"], f"/session/{sid}", lock_message(db, sid))
    db.execute(text("""DELETE FROM solidarity.budget_line
                       WHERE id = :l AND session_id = :s"""), {"l": lid, "s": sid})
    db.commit()
    return back(init["slug"], f"/session/{sid}")


@router.post("/session/{sid}/delete")
def delete_session(sid: int, request: Request,
                   user: User = Depends(require_facilitator),
                   init=Depends(resolve_initiative),
                   db: Session = Depends(get_db)):
    """Delete a session that holds no pledges and has no settlement.

    Budget lines, tokens and empty rounds go with it: none of them is a
    commitment by anyone. The offering it financed is untouched and
    remains, simply no longer financed this way.
    """
    session_of(db, sid, init)
    blocked = session_delete_block(db, sid)
    if blocked:
        return back(init["slug"], f"/session/{sid}", blocked)
    db.execute(text("DELETE FROM solidarity.camp_session WHERE id = :i"), {"i": sid})
    db.commit()
    return back(init["slug"], "/")


@router.post("/session/{sid}/details")
def edit_session_details(sid: int, request: Request, label: str = Form(...),
                         days: str = Form(""), adopted_on: str = Form(""),
                         description: str = Form(""),
                         user: User = Depends(require_facilitator),
                         init=Depends(resolve_initiative),
                         db: Session = Depends(get_db)):
    """Edit the session label, length, adoption date and description.

    Not subject to the budget freeze: the description is not a figure.
    What the session offers may need clarifying at any point, and doing
    so changes nothing anyone pledged against.
    """
    session_of(db, sid, init)
    clash = one(db, """SELECT 1 FROM solidarity.camp_session
                       WHERE label = :l AND id <> :i""", l=label.strip(), i=sid)
    if clash:
        return back(init["slug"], f"/session/{sid}", "another session already has that label")
    try:
        db.execute(text("""UPDATE solidarity.camp_session
                           SET label = :l, days = :d, adopted_on = :a, description = :desc
                           WHERE id = :i"""),
                   {"l": label.strip(), "d": int(days) if days.strip() else None,
                    "a": adopted_on or None, "desc": description.strip(), "i": sid})
        db.commit()
    except ValueError:
        db.rollback()
        return back(init["slug"], f"/session/{sid}", "days must be a whole number")
    return back(init["slug"], f"/session/{sid}")


@router.post("/round/{rid}/delete")
def delete_round(rid: int, request: Request,
                 user: User = Depends(require_facilitator),
                 init=Depends(resolve_initiative),
                 db: Session = Depends(get_db)):
    """Delete a round that holds no pledges, unfreezing the budget.

    Permitted only while the round is empty. An empty round has asked
    nothing of anyone: no family has committed against the figures, so
    removing it breaks no promise and the budget may be corrected. Once
    a single pledge exists the round is permanent — deleting it would
    erase what a family committed and quietly move the figure they
    committed against.
    """
    r = one(db, """SELECT br.* FROM solidarity.bidding_round br
                   JOIN solidarity.camp_session cs ON cs.id = br.session_id
                   WHERE br.id = :i AND cs.initiative_id = :n""",
            i=rid, n=init["id"])
    if not r:
        raise HTTPException(404)
    sid = r["session_id"]
    n = one(db, "SELECT COUNT(*) AS n FROM solidarity.pledge WHERE round_id = :i", i=rid)
    if int(n["n"]) > 0:
        return back(init["slug"], f"/session/{sid}",
                    "This round holds pledges and cannot be deleted. Families have "
                    "committed against these figures; record any correction in the "
                    "settlement account.")
    db.execute(text("DELETE FROM solidarity.bidding_round WHERE id = :i"), {"i": rid})
    db.commit()
    return back(init["slug"], f"/session/{sid}")


@router.post("/session/{sid}/new-round")
def new_round(sid: int, user: User = Depends(require_facilitator),
              init=Depends(resolve_initiative),
              db: Session = Depends(get_db)):
    session_of(db, sid, init)
    db.execute(text("""INSERT INTO solidarity.bidding_round (session_id, round_no, held_on)
                       SELECT :s, COALESCE(MAX(round_no), 0) + 1, CURRENT_DATE
                       FROM solidarity.bidding_round WHERE session_id = :s"""), {"s": sid})
    db.commit()
    return RedirectResponse(url=f"{PREFIX}/session/{sid}", status_code=303)


# ── tokens (mapping optional — may stay on paper) ────────────

@router.get("/session/{sid}/tokens", response_class=HTMLResponse)
def tokens(sid: int, request: Request, user: User = Depends(require_facilitator),
           init=Depends(resolve_initiative),
           db: Session = Depends(get_db)):
    s = session_of(db, sid, init)
    toks = rows(db, """SELECT rt.token,
                       CASE WHEN tm.token_id IS NULL THEN 'on paper' ELSE 'in registry' END AS mapping
                       FROM solidarity.round_token rt
                       LEFT JOIN solidarity.token_mapping tm ON tm.token_id = rt.id
                       WHERE rt.session_id = :i ORDER BY rt.token""", i=sid)
    return render("tokens.html", request, user, init, s=s, toks=toks,
                  error=request.query_params.get("error", ""))


@router.post("/session/{sid}/tokens")
def add_token(sid: int, request: Request, token: str = Form(...),
              household: str = Form(""),
              user: User = Depends(require_facilitator),
              init=Depends(resolve_initiative),
              db: Session = Depends(get_db)):
    session_of(db, sid, init)
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
    return back(init["slug"], f"/session/{sid}/tokens")


# ── rounds + pledges (sums only on screen) ───────────────────

@router.get("/round/{rid}", response_class=HTMLResponse)
def round_view(rid: int, request: Request,
               user: User = Depends(require_facilitator),
               init=Depends(resolve_initiative),
               db: Session = Depends(get_db)):
    r = one(db, """SELECT br.*, cs.label FROM solidarity.bidding_round br
                   JOIN solidarity.camp_session cs ON cs.id = br.session_id
                   WHERE br.id = :i AND cs.initiative_id = :n""",
            i=rid, n=init["id"])
    if not r:
        raise HTTPException(404)
    vt = one(db, "SELECT * FROM solidarity.v_round_totals WHERE round_id = :i", i=rid)
    return render("round.html", request, user, init, r=r, vt=vt,
                  error=request.query_params.get("error", ""))


@router.post("/round/{rid}/pledge")
def enter_pledge(rid: int, request: Request, token: str = Form(...),
                 amount_uah: str = Form(...),
                 user: User = Depends(require_facilitator),
                 init=Depends(resolve_initiative),
                 db: Session = Depends(get_db)):
    r = one(db, """SELECT br.* FROM solidarity.bidding_round br
                   JOIN solidarity.camp_session cs ON cs.id = br.session_id
                   WHERE br.id = :i AND cs.initiative_id = :n""",
            i=rid, n=init["id"])
    if not r or r["state"] != "open":
        return back(init["slug"], f"/round/{rid}", "round is not open")
    tok = one(db, """SELECT id FROM solidarity.round_token
                     WHERE session_id = :s AND token = :t""",
              s=r["session_id"], t=token.strip())
    if not tok:
        return back(init["slug"], f"/round/{rid}",
                    "unknown token for this session — add it on the tokens page first")
    try:
        db.execute(text("""INSERT INTO solidarity.pledge (round_id, token_id, amount_uah)
                           VALUES (:r, :t, :a)
                           ON CONFLICT (round_id, token_id)
                           DO UPDATE SET amount_uah = EXCLUDED.amount_uah"""),
                   {"r": rid, "t": tok["id"], "a": parse_amount(amount_uah)})
        db.commit()
    except ValueError as e:
        return back(init["slug"], f"/round/{rid}", str(e))
    return back(init["slug"], f"/round/{rid}")


@router.post("/round/{rid}/state")
def round_state(rid: int, request: Request, action: str = Form(...),
                user: User = Depends(require_facilitator),
                init=Depends(resolve_initiative),
                db: Session = Depends(get_db)):
    if action not in ("close", "stop"):
        raise HTTPException(400)
    owned = one(db, """SELECT br.id FROM solidarity.bidding_round br
                       JOIN solidarity.camp_session cs ON cs.id = br.session_id
                       WHERE br.id = :i AND cs.initiative_id = :n""",
                i=rid, n=init["id"])
    if not owned:
        raise HTTPException(404)
    db.execute(text("UPDATE solidarity.bidding_round SET state = :st WHERE id = :i"),
               {"st": "closed" if action == "close" else "stopped", "i": rid})
    db.commit()
    return back(init["slug"], f"/round/{rid}")


# ── supporter circle ─────────────────────────────────────────

@router.get("/supporters", response_class=HTMLResponse)
def supporters(request: Request, user: User = Depends(require_facilitator),
               init=Depends(resolve_initiative),
               db: Session = Depends(get_db)):
    return render("supporters.html", request, user, init,
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
                  init=Depends(resolve_initiative),
                  db: Session = Depends(get_db)):
    exists = one(db, "SELECT 1 FROM solidarity.supporter WHERE token = :t", t=token.strip())
    if exists:
        return back(init["slug"], "/supporters", "supporter token already exists")
    db.execute(text("""INSERT INTO solidarity.supporter (token, display_name, note)
                       VALUES (:t, :d, :n)"""),
               {"t": token.strip(), "d": display_name.strip() or None, "n": note})
    db.commit()
    return back(init["slug"], "/supporters")


@router.post("/supporters/contribution")
def add_contribution(request: Request, token: str = Form(...), period: str = Form(...),
                     amount_uah: str = Form(...), status: str = Form(""),
                     note: str = Form(""),
                     user: User = Depends(require_facilitator),
                     init=Depends(resolve_initiative),
                     db: Session = Depends(get_db)):
    sup = one(db, "SELECT id FROM solidarity.supporter WHERE token = :t", t=token.strip())
    if not sup:
        return back(init["slug"], "/supporters", "unknown supporter token — add the supporter first")
    try:
        db.execute(text("""INSERT INTO solidarity.contribution
                           (supporter_id, period, amount_uah, status, note)
                           VALUES (:s, :p, :a, :st, :n)"""),
                   {"s": sup["id"], "p": period.strip(), "a": parse_amount(amount_uah),
                    "st": need_status(status), "n": note})
        db.commit()
    except ValueError as e:
        db.rollback()
        return back(init["slug"], "/supporters", str(e))
    except Exception:
        db.rollback()
        return back(init["slug"], "/supporters", "period must be YYYY-MM")
    return back(init["slug"], "/supporters")


# ── settlement + report ──────────────────────────────────────

@router.get("/session/{sid}/settlement", response_class=HTMLResponse)
def settlement_view(sid: int, request: Request,
                    user: User = Depends(require_facilitator),
                    init=Depends(resolve_initiative),
                    db: Session = Depends(get_db)):
    s = session_of(db, sid, init)
    stl = one(db, "SELECT * FROM solidarity.settlement WHERE session_id = :i", i=sid)
    return render("settlement.html", request, user, init, s=s, stl=stl,
                  error=request.query_params.get("error", ""))


@router.post("/session/{sid}/settlement")
def settlement_save(sid: int, request: Request,
                    received_uah: str = Form(...), outstanding_uah: str = Form(...),
                    spent_uah: str = Form(...), to_infrastructure_uah: str = Form(...),
                    carried_by_hosts_uah: str = Form(...), note: str = Form(""),
                    user: User = Depends(require_facilitator),
                    init=Depends(resolve_initiative),
                    db: Session = Depends(get_db)):
    try:
        vals = {k: parse_amount(v) for k, v in [
            ("r", received_uah), ("o", outstanding_uah), ("sp", spent_uah),
            ("ti", to_infrastructure_uah), ("ch", carried_by_hosts_uah)]}
    except ValueError as e:
        return back(init["slug"], f"/session/{sid}/settlement", str(e))
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
    return back(init["slug"], f"/session/{sid}/settlement")


@router.get("/report/{sid}", response_class=HTMLResponse)
def report(sid: int, request: Request, user: User = Depends(require_facilitator),
           init=Depends(resolve_initiative),
           db: Session = Depends(get_db)):
    session_of(db, sid, init)
    vb = one(db, "SELECT * FROM solidarity.v_session_budget WHERE session_id = :i", i=sid)
    if not vb:
        raise HTTPException(404)
    return render("report.html", request, user, init, vb=vb,
        rounds=rows(db, """SELECT * FROM solidarity.v_round_totals
                           WHERE session_id = :i ORDER BY round_no""", i=sid),
        periods=rows(db, "SELECT * FROM solidarity.v_period_summary ORDER BY period"))


# ── chooser: which initiative? ───────────────────────────────

@chooser.get("/solidarity", response_class=HTMLResponse)
def choose_initiative(request: Request,
                      user: User = Depends(require_facilitator),
                      db: Session = Depends(get_db)):
    """List initiatives with a link into each one's solidarity module.

    Counts are per initiative and are sums only, like every other screen
    here: how many sessions exist, not what anyone pledged.
    """
    if has_global_oversight(user):
        inits = rows(db, """SELECT i.id, i.slug, i.name, i.location,
                                   COUNT(cs.id) AS sessions
                            FROM erdpuls_threshold.initiatives i
                            LEFT JOIN solidarity.camp_session cs ON cs.initiative_id = i.id
                            GROUP BY i.id, i.slug, i.name, i.location, i.sort_order
                            ORDER BY i.sort_order""")
    else:
        inits = rows(db, """SELECT i.id, i.slug, i.name, i.location,
                                   COUNT(cs.id) AS sessions
                            FROM erdpuls_threshold.initiatives i
                            JOIN erdpuls_threshold.initiative_members m
                              ON m.initiative_id = i.id AND m.user_id = :u
                             AND m.role IN ('facilitator', 'steward')
                            LEFT JOIN solidarity.camp_session cs ON cs.initiative_id = i.id
                            GROUP BY i.id, i.slug, i.name, i.location, i.sort_order
                            ORDER BY i.sort_order""", u=str(user.id))
    return templates.TemplateResponse("solidarity/choose.html", {
        "request": request, "user": user, "initiatives": inits,
        "statuses": VALID_STATUSES})
