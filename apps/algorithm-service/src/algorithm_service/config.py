from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from sqlalchemy import URL


class Settings(BaseSettings):
    pghost: str = "localhost"
    pgport: int = 5432
    pgdatabase: str = "algorithm_lab"
    pguser: str = "execution_app"
    pgpassword: SecretStr
    pgsslmode: str = "prefer"
    data_service_url: str = "http://localhost:8080"
    worker_poll_interval: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    worker_error_retry_interval: float = Field(default=5.0, gt=0, allow_inf_nan=False)
    worker_lease_seconds: int = Field(default=30, gt=0)

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.pguser,
            password=self.pgpassword.get_secret_value(),
            host=self.pghost,
            port=self.pgport,
            database=self.pgdatabase,
            query={"sslmode": self.pgsslmode},
        )
