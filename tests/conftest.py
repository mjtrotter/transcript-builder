"""
Pytest Configuration and Fixtures

Provides common fixtures for all tests including:
- Database sessions
- Test data factories
- API client
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from transcript_builder.api.database.models import Base, Tenant, User
from transcript_builder.api.main import app
from transcript_builder.api.database.session import get_db
from transcript_builder.api.routes.auth import get_password_hash

# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test"""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant"""
    tenant = Tenant(
        id=uuid4(),
        name="Test School",
        subdomain="test",
        address="123 Test St",
        city="Test City",
        state="FL",
        phone="555-1234",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user"""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="test@test.com",
        password_hash=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_course_weights():
    """Sample course weight data for GPA tests"""
    from transcript_builder.core.models import CourseWeight

    return {
        "ENG101": CourseWeight(
            course_id=1,
            course_code="ENG101",
            course_title="English 9",
            core=True,
            weight=0.0,
            credit=1.0,
        ),
        "ENG102H": CourseWeight(
            course_id=2,
            course_code="ENG102H",
            course_title="English 10 Honors",
            core=True,
            weight=0.5,
            credit=1.0,
        ),
        "APENG": CourseWeight(
            course_id=3,
            course_code="APENG",
            course_title="AP English",
            core=True,
            weight=1.0,
            credit=1.0,
        ),
        "MATH101": CourseWeight(
            course_id=4,
            course_code="MATH101",
            course_title="Algebra 1",
            core=True,
            weight=0.0,
            credit=1.0,
        ),
        "PE101": CourseWeight(
            course_id=5,
            course_code="PE101",
            course_title="Physical Education",
            core=False,
            weight=0.0,
            credit=0.5,
        ),
    }


@pytest.fixture
def sample_grades(sample_course_weights):
    """Sample grade data for GPA tests"""
    from transcript_builder.core.models import CourseGrade

    return [
        CourseGrade(
            user_id=1001,
            first_name="Test",
            last_name="Student",
            grad_year=2025,
            school_year="2023 - 2024",
            course_code="ENG101",
            course_title="English 9",
            course_part_number="1",
            term_name="Fall",
            grade="A",
            credits_attempted="0.5",
        ),
        CourseGrade(
            user_id=1001,
            first_name="Test",
            last_name="Student",
            grad_year=2025,
            school_year="2023 - 2024",
            course_code="ENG101",
            course_title="English 9",
            course_part_number="2",
            term_name="Spring",
            grade="A",
            credits_attempted="0.5",
        ),
        CourseGrade(
            user_id=1001,
            first_name="Test",
            last_name="Student",
            grad_year=2025,
            school_year="2023 - 2024",
            course_code="MATH101",
            course_title="Algebra 1",
            course_part_number="1",
            term_name="Fall",
            grade="B",
            credits_attempted="0.5",
        ),
        CourseGrade(
            user_id=1001,
            first_name="Test",
            last_name="Student",
            grad_year=2025,
            school_year="2023 - 2024",
            course_code="MATH101",
            course_title="Algebra 1",
            course_part_number="2",
            term_name="Spring",
            grade="B+",
            credits_attempted="0.5",
        ),
    ]
