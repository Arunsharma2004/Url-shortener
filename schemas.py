from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    original_url: str

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Reject any URL that isn't http/https. Returns the original string
        unchanged (not the parsed URL) so the redirect target is stored
        exactly as submitted.
        """
        try:
            HttpUrl(v)
        except Exception as exc:
            raise ValueError("original_url must be a valid http or https URL") from exc
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class StatsResponse(BaseModel):
    original_url: str
    click_count: int
