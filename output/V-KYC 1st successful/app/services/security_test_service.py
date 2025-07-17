import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_

from app.models.security_test import SecurityTest, Vulnerability, Finding, User, TestStatus, UserRole
from app.schemas.security_test import (
    SecurityTestCreate, SecurityTestUpdate,
    VulnerabilityCreate, VulnerabilityUpdate,
    FindingCreate, FindingUpdate
)
from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException, BadRequestException

logger = logging.getLogger(__name__)

class SecurityTestService:
    """
    Service layer for managing security tests, vulnerabilities, and findings.
    Handles business logic and interacts with the database.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    # --- Security Test Operations ---

    async def create_security_test(self, test_data: SecurityTestCreate, current_user: User) -> SecurityTest:
        """Creates a new security test."""
        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can create security tests.")

        # Optional: Check for existing test with same name if name must be unique
        # existing_test = await self.db_session.execute(
        #     select(SecurityTest).filter(SecurityTest.name == test_data.name)
        # )
        # if existing_test.scalars().first():
        #     raise ConflictException(detail=f"Security test with name '{test_data.name}' already exists.")

        db_test = SecurityTest(**test_data.model_dump())
        self.db_session.add(db_test)
        await self.db_session.commit()
        await self.db_session.refresh(db_test)
        logger.info(f"Security test '{db_test.name}' (ID: {db_test.id}) created by user {current_user.username}.")
        return db_test

    async def get_security_test(self, test_id: int) -> Optional[SecurityTest]:
        """Fetches a security test by ID."""
        result = await self.db_session.execute(
            select(SecurityTest).filter(SecurityTest.id == test_id).options(
                # Eager load assigned user for response schema
                # selectinload(SecurityTest.assigned_to_user)
            )
        )
        test = result.scalars().first()
        if not test:
            logger.warning(f"Security test with ID {test_id} not found.")
        return test

    async def get_all_security_tests(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        test_type: Optional[str] = None,
        status: Optional[TestStatus] = None,
        assigned_to: Optional[int] = None
    ) -> List[SecurityTest]:
        """Fetches all security tests with filtering and pagination."""
        query = select(SecurityTest)
        if name:
            query = query.filter(SecurityTest.name.ilike(f"%{name}%"))
        if test_type:
            query = query.filter(SecurityTest.test_type.ilike(f"%{test_type}%"))
        if status:
            query = query.filter(SecurityTest.status == status)
        if assigned_to:
            query = query.filter(SecurityTest.assigned_to == assigned_to)

        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_security_test(self, test_id: int, test_data: SecurityTestUpdate, current_user: User) -> SecurityTest:
        """Updates an existing security test."""
        db_test = await self.get_security_test(test_id)
        if not db_test:
            raise NotFoundException(detail=f"Security test with ID {test_id} not found.")

        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can update security tests.")
        
        # Prevent status changes that are not allowed
        if test_data.status and db_test.status == TestStatus.COMPLETED and test_data.status != TestStatus.COMPLETED:
            raise BadRequestException(detail="Cannot change status of a completed test.")
        if test_data.status and db_test.status == TestStatus.CANCELLED and test_data.status != TestStatus.CANCELLED:
            raise BadRequestException(detail="Cannot change status of a cancelled test.")

        update_data = test_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_test, key, value)

        self.db_session.add(db_test)
        await self.db_session.commit()
        await self.db_session.refresh(db_test)
        logger.info(f"Security test '{db_test.name}' (ID: {db_test.id}) updated by user {current_user.username}.")
        return db_test

    async def delete_security_test(self, test_id: int, current_user: User) -> None:
        """Deletes a security test and its associated vulnerabilities and findings."""
        db_test = await self.get_security_test(test_id)
        if not db_test:
            raise NotFoundException(detail=f"Security test with ID {test_id} not found.")

        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can delete security tests.")

        await self.db_session.delete(db_test)
        await self.db_session.commit()
        logger.info(f"Security test '{db_test.name}' (ID: {db_test.id}) deleted by user {current_user.username}.")

    # --- Vulnerability Operations ---

    async def create_vulnerability(self, vuln_data: VulnerabilityCreate, current_user: User) -> Vulnerability:
        """Creates a new vulnerability for a security test."""
        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can create vulnerabilities.")

        security_test = await self.get_security_test(vuln_data.security_test_id)
        if not security_test:
            raise NotFoundException(detail=f"Security test with ID {vuln_data.security_test_id} not found.")
        
        if security_test.status in [TestStatus.COMPLETED, TestStatus.CANCELLED]:
            raise BadRequestException(detail="Cannot add vulnerabilities to a completed or cancelled test.")

        db_vulnerability = Vulnerability(**vuln_data.model_dump())
        db_vulnerability.reported_by = current_user.id # Assign reporter
        self.db_session.add(db_vulnerability)
        await self.db_session.commit()
        await self.db_session.refresh(db_vulnerability)
        logger.info(f"Vulnerability '{db_vulnerability.name}' (ID: {db_vulnerability.id}) created for test {security_test.id} by user {current_user.username}.")
        return db_vulnerability

    async def get_vulnerability(self, vuln_id: int) -> Optional[Vulnerability]:
        """Fetches a vulnerability by ID."""
        result = await self.db_session.execute(
            select(Vulnerability).filter(Vulnerability.id == vuln_id)
        )
        vuln = result.scalars().first()
        if not vuln:
            logger.warning(f"Vulnerability with ID {vuln_id} not found.")
        return vuln

    async def get_vulnerabilities_by_test(self, test_id: int, skip: int = 0, limit: int = 100) -> List[Vulnerability]:
        """Fetches all vulnerabilities for a specific security test."""
        query = select(Vulnerability).filter(Vulnerability.security_test_id == test_id)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_vulnerability(self, vuln_id: int, vuln_data: VulnerabilityUpdate, current_user: User) -> Vulnerability:
        """Updates an existing vulnerability."""
        db_vulnerability = await self.get_vulnerability(vuln_id)
        if not db_vulnerability:
            raise NotFoundException(detail=f"Vulnerability with ID {vuln_id} not found.")

        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can update vulnerabilities.")

        update_data = vuln_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_vulnerability, key, value)

        self.db_session.add(db_vulnerability)
        await self.db_session.commit()
        await self.db_session.refresh(db_vulnerability)
        logger.info(f"Vulnerability '{db_vulnerability.name}' (ID: {db_vulnerability.id}) updated by user {current_user.username}.")
        return db_vulnerability

    async def delete_vulnerability(self, vuln_id: int, current_user: User) -> None:
        """Deletes a vulnerability and its associated findings."""
        db_vulnerability = await self.get_vulnerability(vuln_id)
        if not db_vulnerability:
            raise NotFoundException(detail=f"Vulnerability with ID {vuln_id} not found.")

        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can delete vulnerabilities.")

        await self.db_session.delete(db_vulnerability)
        await self.db_session.commit()
        logger.info(f"Vulnerability '{db_vulnerability.name}' (ID: {db_vulnerability.id}) deleted by user {current_user.username}.")

    # --- Finding Operations ---

    async def create_finding(self, finding_data: FindingCreate, current_user: User) -> Finding:
        """Creates a new finding for a vulnerability."""
        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can create findings.")

        vulnerability = await self.get_vulnerability(finding_data.vulnerability_id)
        if not vulnerability:
            raise NotFoundException(detail=f"Vulnerability with ID {finding_data.vulnerability_id} not found.")
        
        # Optional: Check if parent test is completed/cancelled
        security_test = await self.get_security_test(vulnerability.security_test_id)
        if security_test and security_test.status in [TestStatus.COMPLETED, TestStatus.CANCELLED]:
            raise BadRequestException(detail="Cannot add findings to a vulnerability belonging to a completed or cancelled test.")

        db_finding = Finding(**finding_data.model_dump())
        db_finding.reported_by = current_user.id # Assign reporter
        self.db_session.add(db_finding)
        await self.db_session.commit()
        await self.db_session.refresh(db_finding)
        logger.info(f"Finding '{db_finding.title}' (ID: {db_finding.id}) created for vulnerability {vulnerability.id} by user {current_user.username}.")
        return db_finding

    async def get_finding(self, finding_id: int) -> Optional[Finding]:
        """Fetches a finding by ID."""
        result = await self.db_session.execute(
            select(Finding).filter(Finding.id == finding_id)
        )
        finding = result.scalars().first()
        if not finding:
            logger.warning(f"Finding with ID {finding_id} not found.")
        return finding

    async def get_findings_by_vulnerability(self, vuln_id: int, skip: int = 0, limit: int = 100) -> List[Finding]:
        """Fetches all findings for a specific vulnerability."""
        query = select(Finding).filter(Finding.vulnerability_id == vuln_id)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_finding(self, finding_id: int, finding_data: FindingUpdate, current_user: User) -> Finding:
        """Updates an existing finding."""
        db_finding = await self.get_finding(finding_id)
        if not db_finding:
            raise NotFoundException(detail=f"Finding with ID {finding_id} not found.")

        if current_user.role not in [UserRole.ADMIN, UserRole.TESTER]:
            raise ForbiddenException(detail="Only administrators or testers can update findings.")

        update_data = finding_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_finding, key, value)

        self.db_session.add(db_finding)
        await self.db_session.commit()
        await self.db_session.refresh(db_finding)
        logger.info(f"Finding '{db_finding.title}' (ID: {db_finding.id}) updated by user {current_user.username}.")
        return db_finding

    async def delete_finding(self, finding_id: int, current_user: User) -> None:
        """Deletes a finding."""
        db_finding = await self.get_finding(finding_id)
        if not db_finding:
            raise NotFoundException(detail=f"Finding with ID {finding_id} not found.")

        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can delete findings.")

        await self.db_session.delete(db_finding)
        await self.db_session.commit()
        logger.info(f"Finding '{db_finding.title}' (ID: {db_finding.id}) deleted by user {current_user.username}.")