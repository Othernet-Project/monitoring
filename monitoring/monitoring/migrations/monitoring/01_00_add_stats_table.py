SQL = """
create table stats
(
    ip varchar,                         -- IP address
    location varchar,                   -- client location
    client_id varchar,                  -- client ID
    signal_lock boolean,                -- signal lock
    service_lock boolean,               -- service lock
    bitrate integer,                    -- service bitrate
    snr float,                          -- signal/noise ratio
    service_ok boolean,                 -- final verdict
    tuner_vendor varchar,               -- tuner vendor id
    tuner_model varchar,                -- tuner model id
    tuner_preset integer,               -- tuner preset id
    carousels_count integer,            -- number of carousels
    carousels_status boolean[],         -- carousels statuses
    timestamp integer,                  -- heartbeat timestamp
    reported integer                    -- heartbeat timestamp
);
"""


def up(db, conf):
    db.executescript(SQL)
