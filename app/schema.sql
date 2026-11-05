DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS client_requests;
DROP TABLE IF EXISTS availability;
DROP TABLE IF EXISTS experts;

CREATE TABLE experts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    slug             TEXT    NOT NULL UNIQUE,
    name             TEXT    NOT NULL,
    title            TEXT    NOT NULL,
    hub              TEXT    NOT NULL,          -- Nairobi | Addis Ababa | Atlanta | Berlin
    category         TEXT    NOT NULL,          -- see app/constants.py CATEGORIES
    skills           TEXT    NOT NULL,          -- comma-separated tags
    bio              TEXT    NOT NULL,
    languages        TEXT    NOT NULL,
    years_experience INTEGER NOT NULL,
    rate             INTEGER NOT NULL,          -- per one-hour session
    currency         TEXT    NOT NULL DEFAULT 'KES',
    rating           REAL    NOT NULL DEFAULT 0,
    sessions_done    INTEGER NOT NULL DEFAULT 0,
    is_active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE availability (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    expert_id  INTEGER NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
    start_at   TEXT    NOT NULL,                -- ISO 8601, UTC
    is_booked  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (expert_id, start_at)
);

CREATE TABLE client_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ref         TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL,
    phone       TEXT    NOT NULL,
    company     TEXT,
    category    TEXT    NOT NULL,
    description TEXT    NOT NULL,
    hub_pref    TEXT,
    status      TEXT    NOT NULL DEFAULT 'new', -- new | matched | closed
    created_at  TEXT    NOT NULL
);

CREATE TABLE bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ref            TEXT    NOT NULL UNIQUE,
    expert_id      INTEGER NOT NULL REFERENCES experts(id),
    slot_id        INTEGER NOT NULL REFERENCES availability(id),
    request_id     INTEGER REFERENCES client_requests(id),
    client_name    TEXT    NOT NULL,
    email          TEXT    NOT NULL,
    phone          TEXT    NOT NULL,
    notes          TEXT,
    amount         INTEGER NOT NULL,
    currency       TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'pending',  -- pending | confirmed | completed | cancelled
    payment_status TEXT    NOT NULL DEFAULT 'unpaid',   -- unpaid | requested | paid
    payment_ref    TEXT,
    created_at     TEXT    NOT NULL
);

CREATE INDEX idx_availability_expert ON availability(expert_id, start_at);
CREATE INDEX idx_bookings_status ON bookings(status);
