CREATE TABLE catalog.scenario_version
(
    id          UUID PRIMARY KEY,
    scenario_id UUID         NOT NULL,
    showcase_id VARCHAR(16)  NOT NULL
        REFERENCES catalog.showcase (id),
    version     INTEGER      NOT NULL CHECK (version > 0),
    name        VARCHAR(128) NOT NULL,
    input       JSONB        NOT NULL CHECK (jsonb_typeof(input) = 'object'),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (scenario_id, version)
);

INSERT INTO catalog.scenario_version (id,
                                      scenario_id,
                                      showcase_id,
                                      version,
                                      name,
                                      input)
VALUES ('00000000-0000-4000-8000-000000000010',
        '00000000-0000-4000-8000-000000000001',
        'K01',
        1,
        'Fibonacci with n = 10',
        '{
          "n": 10
        }');

CREATE FUNCTION catalog.reject_scenario_version_change()
    RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    RAISE
EXCEPTION 'Scenario versions are immutable';
RETURN NULL;
END;
$$;

CREATE TRIGGER scenario_version_immutable
    BEFORE UPDATE OR
DELETE
ON catalog.scenario_version
FOR EACH ROW
EXECUTE FUNCTION catalog.reject_scenario_version_change();