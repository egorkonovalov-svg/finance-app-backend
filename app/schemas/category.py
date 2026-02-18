from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=50)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    type: str = Field(pattern="^(income|expense|both)$")


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    type: str | None = Field(default=None, pattern="^(income|expense|both)$")


class CategoryResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    type: str

    model_config = {"from_attributes": True}
