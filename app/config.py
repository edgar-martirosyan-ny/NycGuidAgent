from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    ALLOWED_ORIGINS: str = "http://localhost:4200"
    PEXELS_URL: str
    PEXELS_TOKEN: str
    BACKEND_BASE_URL: str
    FILE_UPLOAD_URL: str
    OPENAI_API_KEY: str

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
