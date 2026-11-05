import pytest

from app import create_app
from app.db import get_db, init_db
from app.matching import guess_category, match_experts
from app.payments import normalize_phone
from app.seed import seed

TOKEN = "test-token"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "ADMIN_PASSWORD": "secret",
        "SECRET_KEY": "test",
    })
    with app.app_context():
        init_db()
        seed(get_db())
    return app


@pytest.fixture
def client(app):
    c = app.test_client()
    with c.session_transaction() as s:
        s["_csrf"] = TOKEN
    return c


def first_open_slot(app, slug):
    with app.app_context():
        return get_db().execute(
            """SELECT a.id FROM availability a JOIN experts e ON e.id = a.expert_id
               WHERE e.slug = ? AND a.is_booked = 0 ORDER BY a.start_at LIMIT 1""",
            (slug,),
        ).fetchone()["id"]


def booking_form(slot_id, **extra):
    data = {"_csrf": TOKEN, "slot_id": slot_id, "name": "Achieng Otieno",
            "email": "achieng@example.co.ke", "phone": "0712 345 678"}
    data.update(extra)
    return data


# Pages

@pytest.mark.parametrize("path", ["/", "/experts", "/experts/wanjiku-kamau", "/request", "/admin/login"])
def test_pages_load(client, path):
    assert client.get(path).status_code == 200


def test_unknown_expert_is_404(client):
    assert client.get("/experts/nobody").status_code == 404


def test_directory_filters(client):
    html = client.get("/experts?hub=Berlin").get_data(as_text=True)
    assert "Lena Hoffmann" in html and "Wanjiku Kamau" not in html
    html = client.get("/experts?q=pitch").get_data(as_text=True)
    assert "Otieno Odhiambo" in html and "Lena Hoffmann" not in html


def test_foreign_hub_slots_show_nairobi_time(client):
    html = client.get("/experts/lena-hoffmann").get_data(as_text=True)
    assert "Nairobi time is shown in brackets" in html


def test_same_timezone_hub_skips_nairobi_time(client):
    # Addis Ababa and Nairobi share a clock, so no conversion is shown.
    html = client.get("/experts/selam-tesfaye").get_data(as_text=True)
    assert "Nairobi time is shown in brackets" not in html


# Booking

def test_booking_happy_path(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    r = client.post("/experts/wanjiku-kamau/book", data=booking_form(slot))
    assert r.status_code == 302 and "/bookings/BK-" in r.location

    page = client.get(r.location).get_data(as_text=True)
    assert "Session requested" in page and "KES 4,500" in page

    with app.app_context():
        b = get_db().execute("SELECT * FROM bookings").fetchone()
        assert b["phone"] == "254712345678"
        assert b["payment_status"] == "requested"
        assert get_db().execute("SELECT is_booked FROM availability WHERE id = ?", (slot,)).fetchone()[0] == 1


def test_same_slot_cannot_be_booked_twice(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    client.post("/experts/wanjiku-kamau/book", data=booking_form(slot))
    r = client.post("/experts/wanjiku-kamau/book", data=booking_form(slot, email="other@example.com"))
    assert r.status_code == 409
    assert "Someone just booked that time" in r.get_data(as_text=True)


def test_slot_must_belong_to_expert(client, app):
    other_slot = first_open_slot(app, "lena-hoffmann")
    r = client.post("/experts/wanjiku-kamau/book", data=booking_form(other_slot))
    assert r.status_code == 400
    assert "Choose a time" in r.get_data(as_text=True)


def test_booking_validates_contact_details(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    r = client.post("/experts/wanjiku-kamau/book",
                    data=booking_form(slot, email="not-an-email", phone="12"))
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "Enter an email address" in html and "Enter a phone number" in html


def test_post_without_csrf_is_rejected(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    data = booking_form(slot)
    data.pop("_csrf")
    assert client.post("/experts/wanjiku-kamau/book", data=data).status_code == 400


# Requests and matching

def test_request_creates_matches(client, app):
    r = client.post("/request", data={
        "_csrf": TOKEN, "name": "Achieng Otieno", "email": "achieng@example.co.ke",
        "phone": "0712345678", "category": "",
        "description": "We make shea butter in Nairobi and want to export to the US. "
                       "Which certifications and distributors do we need?",
    })
    assert r.status_code == 302
    html = client.get(r.location).get_data(as_text=True)
    assert "Monica Reed" in html  # US market entry advisor


def test_booking_from_request_marks_it_matched(client, app):
    r = client.post("/request", data={
        "_csrf": TOKEN, "name": "Achieng", "email": "a@example.com", "phone": "0712345678",
        "category": "legal", "description": "I need help registering my company and drafting contracts.",
    })
    ref = r.location.rsplit("/", 1)[-1]
    slot = first_open_slot(app, "amina-hassan")
    client.post("/experts/amina-hassan/book", data=booking_form(slot, request_ref=ref))
    with app.app_context():
        assert get_db().execute("SELECT status FROM client_requests WHERE ref = ?", (ref,)).fetchone()[0] == "matched"


def test_short_request_is_rejected(client):
    r = client.post("/request", data={"_csrf": TOKEN, "name": "A B", "email": "a@b.co",
                                      "phone": "0712345678", "category": "legal", "description": "help"})
    assert r.status_code == 400


def test_matcher_ranks_relevant_experts(app):
    with app.app_context():
        results = match_experts(get_db(), "finance", "We need a pitch deck to raise from investors")
        assert results[0].expert["slug"] == "otieno-odhiambo"
        assert all(m.relevant for m in results)


def test_guess_category():
    assert guess_category("our KRA tax compliance and contracts") == "legal"
    assert guess_category("hello there") is None


@pytest.mark.parametrize("raw,expected", [
    ("0712 345 678", "254712345678"),
    ("+254 712 345 678", "254712345678"),
    ("0112345678", "254112345678"),
    ("+1 404 555 0100", "14045550100"),
    ("12345", None),
    ("", None),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


# Admin

def login(client):
    return client.post("/admin/login", data={"_csrf": TOKEN, "password": "secret"})


def test_admin_requires_login(client):
    r = client.get("/admin/")
    assert r.status_code == 302 and "/admin/login" in r.location


def test_admin_wrong_password(client):
    r = client.post("/admin/login", data={"_csrf": TOKEN, "password": "wrong"})
    assert "That password is incorrect" in r.get_data(as_text=True)


def test_admin_login_rejects_offsite_redirect(client):
    r = client.post("/admin/login", data={"_csrf": TOKEN, "password": "secret", "next": "https://evil.example"})
    assert r.location.endswith("/admin/")


def test_admin_confirm_pay_and_cancel(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    client.post("/experts/wanjiku-kamau/book", data=booking_form(slot))
    login(client)
    with client.session_transaction() as s:
        s["_csrf"] = TOKEN  # login clears the session

    with app.app_context():
        bid = get_db().execute("SELECT id FROM bookings").fetchone()[0]

    assert "Achieng Otieno" in client.get("/admin/").get_data(as_text=True)

    client.post(f"/admin/bookings/{bid}", data={"_csrf": TOKEN, "action": "confirmed"})
    client.post(f"/admin/bookings/{bid}", data={"_csrf": TOKEN, "action": "mark_paid"})
    with app.app_context():
        b = get_db().execute("SELECT status, payment_status FROM bookings").fetchone()
        assert (b["status"], b["payment_status"]) == ("confirmed", "paid")

    client.post(f"/admin/bookings/{bid}", data={"_csrf": TOKEN, "action": "cancelled"})
    with app.app_context():
        assert get_db().execute("SELECT is_booked FROM availability WHERE id = ?", (slot,)).fetchone()[0] == 0


def test_cancelled_booking_cannot_reopen_if_slot_taken(client, app):
    slot = first_open_slot(app, "wanjiku-kamau")
    client.post("/experts/wanjiku-kamau/book", data=booking_form(slot))
    login(client)
    with client.session_transaction() as s:
        s["_csrf"] = TOKEN
    with app.app_context():
        first = get_db().execute("SELECT id FROM bookings").fetchone()[0]
    client.post(f"/admin/bookings/{first}", data={"_csrf": TOKEN, "action": "cancelled"})
    client.post("/experts/wanjiku-kamau/book", data=booking_form(slot, email="second@example.com"))
    r = client.post(f"/admin/bookings/{first}", data={"_csrf": TOKEN, "action": "pending"}, follow_redirects=True)
    assert "can&#39;t be reopened" in r.get_data(as_text=True)
    with app.app_context():
        assert get_db().execute("SELECT status FROM bookings WHERE id = ?", (first,)).fetchone()[0] == "cancelled"
