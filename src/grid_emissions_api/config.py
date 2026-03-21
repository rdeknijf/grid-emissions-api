from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    entsoe_token: str = ""
    entsoe_base_url: str = "https://web-api.tp.entsoe.eu/api"
    database_path: str = "data/emissions.db"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
