SQL = """
create table stats
(
    ip varchar,                         -- IP address
    location varchar,                   -- client location
    platform varchar,                   -- client platform name
    client_id varchar,                  -- client ID
    service_id varchar,                 -- service identifier
    pid varchar,                        -- service PID
    signal_lock boolean,                -- signal lock
    bitrate integer,                    -- service bitrate
    snr float,                          -- signal/noise ratio
    transfers boolean,                  -- whether there are ongoing transfers
    sat_config varchar,                 -- satellite config checksum
    service_ok boolean,                 -- final verdict
    timestamp integer,                  -- heartbeat timestamp
    processing_time float,              -- total processing time
    reported integer                    -- time reported
);
"""


def up(db, conf):
    db.executescript(SQL)
