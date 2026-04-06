# Writing Good API Metadata

Every Squareberg app exposes an OpenAPI spec generated automatically by FastAPI. That spec powers two consumers simultaneously: the **API explorer** (`/registry/{name}/view`) for human browsing, and any **AI agent** that introspects your app's capabilities before calling it.

Both consumers benefit from the same thing — concise, accurate metadata attached directly to your code.

---

## The principle: enough, not overwhelming

Each endpoint should answer three questions at a glance:

1. **What does this do?** — one-line `summary`
2. **When would I use it / what should I know?** — optional `description` (a sentence or two, not a manual)
3. **What goes in, what comes out?** — typed parameters, typed response models

Avoid writing documentation novels. A clear function name and typed signature often carry more signal than a paragraph of prose.

---

## FastAPI fields that matter

### `summary` and `description`

```python
@router.get(
    "/search",
    summary="Search papers by keyword",
    description="Full-text search across title and abstract. Returns up to 50 results ordered by relevance.",
)
async def search(q: str) -> list[PaperSummary]:
    ...
```

- **`summary`** — shown in the sidebar of the API explorer. Keep it under 60 characters, verb-first: *"Search papers"*, *"Create task"*, *"Delete attachment"*.
- **`description`** — shown in the main panel. One or two sentences about non-obvious behaviour, limits, or side effects. Skip it if the summary already says everything.

### `tags`

Tags group endpoints in the sidebar. Use one tag per logical resource:

```python
router = APIRouter(tags=["papers"])
```

Or per-endpoint if routes span multiple resources:

```python
@router.post("/import", tags=["papers", "import"])
```

Without tags, all endpoints appear in a single flat list. One or two tags per app is usually the right amount.

### `response_model`

Always declare a `response_model`. It generates the response schema in the explorer and forces you to document what you actually return:

```python
class PaperSummary(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int

@router.get("/search", response_model=list[PaperSummary])
async def search(q: str): ...
```

### `responses` — documenting error codes

Document error responses that callers should handle:

```python
@router.get(
    "/{paper_id}",
    response_model=Paper,
    responses={
        404: {"description": "Paper not found"},
        503: {"description": "Storage unavailable"},
    },
)
async def get_paper(paper_id: str): ...
```

---

## Annotating parameters

Use `Query`, `Path`, and `Body` to attach descriptions and constraints directly to parameters:

```python
from fastapi import Query, Path
from pydantic import BaseModel, Field

@router.get("/search")
async def search(
    q: str = Query(description="Search terms, space-separated"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[PaperSummary]:
    ...

@router.get("/{paper_id}")
async def get_paper(
    paper_id: str = Path(description="The paper's unique identifier"),
) -> Paper:
    ...
```

For request bodies, use `Field` inside your Pydantic model:

```python
class CreateTaskRequest(BaseModel):
    title: str = Field(description="Short task title", max_length=120)
    priority: int = Field(1, ge=1, le=5, description="Priority from 1 (low) to 5 (critical)")
    assignee: str | None = Field(None, description="Username of the assignee, or null")
```

---

## The `/api/health` endpoint

Every app must expose a health endpoint. Keep it minimal — its only job is to confirm the process is alive:

```python
@router.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}
```

The `include_in_schema=False` flag hides it from the explorer, since it is infrastructure rather than API surface.

---

## A complete annotated example

```python
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["papers"])


class PaperSummary(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int


class Paper(PaperSummary):
    abstract: str
    doi: str | None = Field(None, description="DOI URI if available")
    pdf_url: str | None = Field(None, description="URL to the PDF, relative to the hub")


@router.get(
    "/search",
    summary="Search papers by keyword",
    response_model=list[PaperSummary],
)
async def search(
    q: str = Query(description="Space-separated search terms"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
) -> list[PaperSummary]:
    """Full-text search across title and abstract, ordered by relevance."""
    ...


@router.get(
    "/{paper_id}",
    summary="Get a paper by ID",
    response_model=Paper,
    responses={404: {"description": "Paper not found"}},
)
async def get_paper(
    paper_id: str = Path(description="Paper identifier"),
) -> Paper:
    ...
```

This produces a well-structured explorer view with a clear sidebar entry per endpoint, typed parameter tables, and documented response codes — without a single line of documentation that isn't also a code constraint.

---

## Checklist

- [ ] Every endpoint has a short `summary`
- [ ] Tags are set at the router level (not repeated per endpoint)
- [ ] All parameters use `Query` / `Path` / `Field` with at least a `description`
- [ ] Every endpoint declares a `response_model`
- [ ] Non-happy-path HTTP codes are listed in `responses`
- [ ] `/api/health` is present and has `include_in_schema=False`
