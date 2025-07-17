from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from models import User, TestProject, VulnerabilityScan, Vulnerability, PenetrationTest, PenetrationTestFinding, UserRole, TestStatus, VulnerabilitySeverity
from schemas import (
    UserCreate, UserUpdate, TestProjectCreate, TestProjectUpdate,
    VulnerabilityScanCreate, VulnerabilityScanUpdate, VulnerabilityCreate, VulnerabilityUpdate,
    PenetrationTestCreate, PenetrationTestUpdate, PenetrationTestFindingCreate, PenetrationTestFindingUpdate
)
from security import get_password_hash, verify_password
from exceptions import NotFoundException, ConflictException, BadRequestException, UnauthorizedException
import logging

logger = logging.getLogger("security_testing_api")

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    async def create_user(self, user_in: UserCreate) -> User:
        existing_user = await self.get_user_by_username(user_in.username)
        if existing_user:
            raise ConflictException(detail=f"Username '{user_in.username}' already registered.")
        existing_email = await self.get_user_by_email(user_in.email)
        if existing_email:
            raise ConflictException(detail=f"Email '{user_in.email}' already registered.")

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' created with role '{db_user.role}'.")
        return db_user

    async def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found.")

        update_data = user_in.model_dump(exclude_unset=True)

        if 'username' in update_data and update_data['username'] != db_user.username:
            if await self.get_user_by_username(update_data['username']):
                raise ConflictException(detail=f"Username '{update_data['username']}' already taken.")
        if 'email' in update_data and update_data['email'] != db_user.email:
            if await self.get_user_by_email(update_data['email']):
                raise ConflictException(detail=f"Email '{update_data['email']}' already taken.")
        if 'password' in update_data:
            update_data['hashed_password'] = get_password_hash(update_data.pop('password'))

        for key, value in update_data.items():
            setattr(db_user, key, value)

        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' (ID: {db_user.id}) updated.")
        return db_user

    async def delete_user(self, user_id: int):
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found.")
        await self.db.delete(db_user)
        await self.db.commit()
        logger.info(f"User '{db_user.username}' (ID: {db_user.id}) deleted.")
        return {"message": "User deleted successfully."}

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = await self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            raise UnauthorizedException(detail="Inactive user")
        return user

class TestProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_by_id(self, project_id: int) -> Optional[TestProject]:
        result = await self.db.execute(
            select(TestProject).where(TestProject.id == project_id).options(
                relationship.selectinload(TestProject.owner)
            )
        )
        return result.scalar_one_or_none()

    async def get_projects(self, skip: int = 0, limit: int = 100, owner_id: Optional[int] = None) -> List[TestProject]:
        query = select(TestProject).options(relationship.selectinload(TestProject.owner))
        if owner_id:
            query = query.where(TestProject.owner_id == owner_id)
        result = await self.db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def create_project(self, project_in: TestProjectCreate, owner_id: int) -> TestProject:
        db_project = TestProject(**project_in.model_dump(), owner_id=owner_id)
        self.db.add(db_project)
        await self.db.commit()
        await self.db.refresh(db_project)
        logger.info(f"Test project '{db_project.name}' (ID: {db_project.id}) created by user {owner_id}.")
        return db_project

    async def update_project(self, project_id: int, project_in: TestProjectUpdate) -> TestProject:
        db_project = await self.get_project_by_id(project_id)
        if not db_project:
            raise NotFoundException(detail="Test project not found.")

        update_data = project_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_project, key, value)

        await self.db.commit()
        await self.db.refresh(db_project)
        logger.info(f"Test project '{db_project.name}' (ID: {db_project.id}) updated.")
        return db_project

    async def delete_project(self, project_id: int):
        db_project = await self.get_project_by_id(project_id)
        if not db_project:
            raise NotFoundException(detail="Test project not found.")
        await self.db.delete(db_project)
        await self.db.commit()
        logger.info(f"Test project '{db_project.name}' (ID: {db_project.id}) deleted.")
        return {"message": "Test project deleted successfully."}

class VulnerabilityScanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_scan_by_id(self, scan_id: int) -> Optional[VulnerabilityScan]:
        result = await self.db.execute(select(VulnerabilityScan).where(VulnerabilityScan.id == scan_id))
        return result.scalar_one_or_none()

    async def get_scans_for_project(self, project_id: int, skip: int = 0, limit: int = 100) -> List[VulnerabilityScan]:
        result = await self.db.execute(
            select(VulnerabilityScan).where(VulnerabilityScan.project_id == project_id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create_scan(self, project_id: int, scan_in: VulnerabilityScanCreate) -> VulnerabilityScan:
        db_scan = VulnerabilityScan(**scan_in.model_dump(), project_id=project_id)
        self.db.add(db_scan)
        await self.db.commit()
        await self.db.refresh(db_scan)
        logger.info(f"Vulnerability scan (ID: {db_scan.id}) created for project {project_id}.")
        return db_scan

    async def update_scan(self, scan_id: int, scan_in: VulnerabilityScanUpdate) -> VulnerabilityScan:
        db_scan = await self.get_scan_by_id(scan_id)
        if not db_scan:
            raise NotFoundException(detail="Vulnerability scan not found.")

        update_data = scan_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_scan, key, value)

        await self.db.commit()
        await self.db.refresh(db_scan)
        logger.info(f"Vulnerability scan (ID: {db_scan.id}) updated.")
        return db_scan

    async def delete_scan(self, scan_id: int):
        db_scan = await self.get_scan_by_id(scan_id)
        if not db_scan:
            raise NotFoundException(detail="Vulnerability scan not found.")
        await self.db.delete(db_scan)
        await self.db.commit()
        logger.info(f"Vulnerability scan (ID: {db_scan.id}) deleted.")
        return {"message": "Vulnerability scan deleted successfully."}

class VulnerabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_vulnerability_by_id(self, vuln_id: int) -> Optional[Vulnerability]:
        result = await self.db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
        return result.scalar_one_or_none()

    async def get_vulnerabilities_for_scan(self, scan_id: int, skip: int = 0, limit: int = 100) -> List[Vulnerability]:
        result = await self.db.execute(
            select(Vulnerability).where(Vulnerability.scan_id == scan_id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create_vulnerability(self, scan_id: int, vuln_in: VulnerabilityCreate) -> Vulnerability:
        db_vuln = Vulnerability(**vuln_in.model_dump(), scan_id=scan_id)
        self.db.add(db_vuln)
        await self.db.commit()
        await self.db.refresh(db_vuln)
        logger.info(f"Vulnerability '{db_vuln.name}' (ID: {db_vuln.id}) created for scan {scan_id}.")
        return db_vuln

    async def update_vulnerability(self, vuln_id: int, vuln_in: VulnerabilityUpdate) -> Vulnerability:
        db_vuln = await self.get_vulnerability_by_id(vuln_id)
        if not db_vuln:
            raise NotFoundException(detail="Vulnerability not found.")

        update_data = vuln_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_vuln, key, value)

        await self.db.commit()
        await self.db.refresh(db_vuln)
        logger.info(f"Vulnerability '{db_vuln.name}' (ID: {db_vuln.id}) updated.")
        return db_vuln

    async def delete_vulnerability(self, vuln_id: int):
        db_vuln = await self.get_vulnerability_by_id(vuln_id)
        if not db_vuln:
            raise NotFoundException(detail="Vulnerability not found.")
        await self.db.delete(db_vuln)
        await self.db.commit()
        logger.info(f"Vulnerability '{db_vuln.name}' (ID: {db_vuln.id}) deleted.")
        return {"message": "Vulnerability deleted successfully."}

class PenetrationTestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_pen_test_by_id(self, pen_test_id: int) -> Optional[PenetrationTest]:
        result = await self.db.execute(
            select(PenetrationTest).where(PenetrationTest.id == pen_test_id).options(
                relationship.selectinload(PenetrationTest.tester)
            )
        )
        return result.scalar_one_or_none()

    async def get_pen_tests_for_project(self, project_id: int, skip: int = 0, limit: int = 100) -> List[PenetrationTest]:
        result = await self.db.execute(
            select(PenetrationTest).where(PenetrationTest.project_id == project_id).options(
                relationship.selectinload(PenetrationTest.tester)
            ).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create_pen_test(self, project_id: int, pen_test_in: PenetrationTestCreate) -> PenetrationTest:
        # Validate tester_id exists
        user_service = UserService(self.db)
        tester = await user_service.get_user_by_id(pen_test_in.tester_id)
        if not tester:
            raise BadRequestException(detail=f"Tester with ID {pen_test_in.tester_id} not found.")

        db_pen_test = PenetrationTest(**pen_test_in.model_dump(), project_id=project_id)
        self.db.add(db_pen_test)
        await self.db.commit()
        await self.db.refresh(db_pen_test)
        logger.info(f"Penetration test (ID: {db_pen_test.id}) created for project {project_id} by tester {pen_test_in.tester_id}.")
        return db_pen_test

    async def update_pen_test(self, pen_test_id: int, pen_test_in: PenetrationTestUpdate) -> PenetrationTest:
        db_pen_test = await self.get_pen_test_by_id(pen_test_id)
        if not db_pen_test:
            raise NotFoundException(detail="Penetration test not found.")

        update_data = pen_test_in.model_dump(exclude_unset=True)
        if 'tester_id' in update_data and update_data['tester_id'] != db_pen_test.tester_id:
            user_service = UserService(self.db)
            tester = await user_service.get_user_by_id(update_data['tester_id'])
            if not tester:
                raise BadRequestException(detail=f"Tester with ID {update_data['tester_id']} not found.")

        for key, value in update_data.items():
            setattr(db_pen_test, key, value)

        await self.db.commit()
        await self.db.refresh(db_pen_test)
        logger.info(f"Penetration test (ID: {db_pen_test.id}) updated.")
        return db_pen_test

    async def delete_pen_test(self, pen_test_id: int):
        db_pen_test = await self.get_pen_test_by_id(pen_test_id)
        if not db_pen_test:
            raise NotFoundException(detail="Penetration test not found.")
        await self.db.delete(db_pen_test)
        await self.db.commit()
        logger.info(f"Penetration test (ID: {db_pen_test.id}) deleted.")
        return {"message": "Penetration test deleted successfully."}

class PenetrationTestFindingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_finding_by_id(self, finding_id: int) -> Optional[PenetrationTestFinding]:
        result = await self.db.execute(select(PenetrationTestFinding).where(PenetrationTestFinding.id == finding_id))
        return result.scalar_one_or_none()

    async def get_findings_for_pen_test(self, pen_test_id: int, skip: int = 0, limit: int = 100) -> List[PenetrationTestFinding]:
        result = await self.db.execute(
            select(PenetrationTestFinding).where(PenetrationTestFinding.pen_test_id == pen_test_id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create_finding(self, pen_test_id: int, finding_in: PenetrationTestFindingCreate) -> PenetrationTestFinding:
        db_finding = PenetrationTestFinding(**finding_in.model_dump(), pen_test_id=pen_test_id)
        self.db.add(db_finding)
        await self.db.commit()
        await self.db.refresh(db_finding)
        logger.info(f"Penetration test finding '{db_finding.name}' (ID: {db_finding.id}) created for pen test {pen_test_id}.")
        return db_finding

    async def update_finding(self, finding_id: int, finding_in: PenetrationTestFindingUpdate) -> PenetrationTestFinding:
        db_finding = await self.get_finding_by_id(finding_id)
        if not db_finding:
            raise NotFoundException(detail="Penetration test finding not found.")

        update_data = finding_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_finding, key, value)

        await self.db.commit()
        await self.db.refresh(db_finding)
        logger.info(f"Penetration test finding '{db_finding.name}' (ID: {db_finding.id}) updated.")
        return db_finding

    async def delete_finding(self, finding_id: int):
        db_finding = await self.get_finding_by_id(finding_id)
        if not db_finding:
            raise NotFoundException(detail="Penetration test finding not found.")
        await self.db.delete(db_finding)
        await self.db.commit()
        logger.info(f"Penetration test finding '{db_finding.name}' (ID: {db_finding.id}) deleted.")
        return {"message": "Penetration test finding deleted successfully."}