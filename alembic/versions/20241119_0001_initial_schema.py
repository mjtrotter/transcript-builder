"""Initial schema - Multi-tenant transcript builder

Revision ID: 0001
Revises:
Create Date: 2024-11-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(100), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=True),
        sa.Column('secondary_color', sa.String(7), nullable=True),
        sa.Column('grading_scale', postgresql.JSON(), nullable=True),
        sa.Column('gpa_config', postgresql.JSON(), nullable=True),
        sa.Column('transcript_config', postgresql.JSON(), nullable=True),
        sa.Column('blackbaud_school_id', sa.String(100), nullable=True),
        sa.Column('blackbaud_access_token', sa.Text(), nullable=True),
        sa.Column('blackbaud_refresh_token', sa.Text(), nullable=True),
        sa.Column('blackbaud_token_expires', sa.DateTime(), nullable=True),
        sa.Column('plan', sa.String(50), nullable=True),
        sa.Column('max_students', sa.Integer(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subdomain')
    )

    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_user_tenant_email')
    )
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'])

    # Students table
    op.create_table('students',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('middle_name', sa.String(100), nullable=True),
        sa.Column('preferred_name', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('graduation_year', sa.Integer(), nullable=False),
        sa.Column('grade_level', sa.String(20), nullable=True),
        sa.Column('enroll_date', sa.Date(), nullable=True),
        sa.Column('depart_date', sa.Date(), nullable=True),
        sa.Column('core_weighted_gpa', sa.Float(), nullable=True),
        sa.Column('core_unweighted_gpa', sa.Float(), nullable=True),
        sa.Column('class_rank', sa.String(50), nullable=True),
        sa.Column('total_credits', sa.Float(), nullable=True),
        sa.Column('service_hours', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'external_id', name='uq_student_tenant_external')
    )
    op.create_index('ix_students_tenant_grad_year', 'students', ['tenant_id', 'graduation_year'])
    op.create_index('ix_students_tenant_name', 'students', ['tenant_id', 'last_name', 'first_name'])

    # Courses table
    op.create_table('courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_code', sa.String(50), nullable=False),
        sa.Column('course_title', sa.String(255), nullable=False),
        sa.Column('credit', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('is_core', sa.Boolean(), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'course_code', name='uq_course_tenant_code')
    )
    op.create_index('ix_courses_tenant_code', 'courses', ['tenant_id', 'course_code'])

    # Course grades table
    op.create_table('course_grades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('course_code', sa.String(50), nullable=False),
        sa.Column('course_title', sa.String(255), nullable=False),
        sa.Column('school_year', sa.String(20), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('term_name', sa.String(50), nullable=True),
        sa.Column('grade', sa.String(10), nullable=False),
        sa.Column('credits_attempted', sa.Float(), nullable=True),
        sa.Column('credits_earned', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_grades_tenant_student', 'course_grades', ['tenant_id', 'student_id'])
    op.create_index('ix_grades_tenant_year', 'course_grades', ['tenant_id', 'school_year'])

    # Transfer grades table
    op.create_table('transfer_grades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_school', sa.String(255), nullable=True),
        sa.Column('course_code', sa.String(50), nullable=True),
        sa.Column('course_title', sa.String(255), nullable=False),
        sa.Column('school_year', sa.String(20), nullable=False),
        sa.Column('grade', sa.String(10), nullable=False),
        sa.Column('credits', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transfer_tenant_student', 'transfer_grades', ['tenant_id', 'student_id'])

    # Templates table
    op.create_table('templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layout', sa.String(50), nullable=True),
        sa.Column('html_template', sa.Text(), nullable=True),
        sa.Column('css_styles', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_templates_tenant', 'templates', ['tenant_id'])

    # Transcripts table
    op.create_table('transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transcript_type', sa.String(50), nullable=True),
        sa.Column('verification_code', sa.String(100), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_to', sa.String(255), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_method', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('verification_code')
    )
    op.create_index('ix_transcripts_tenant_student', 'transcripts', ['tenant_id', 'student_id'])
    op.create_index('ix_transcripts_verification', 'transcripts', ['verification_code'])

    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_tenant_action', 'audit_logs', ['tenant_id', 'action'])
    op.create_index('ix_audit_tenant_created', 'audit_logs', ['tenant_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('transcripts')
    op.drop_table('templates')
    op.drop_table('transfer_grades')
    op.drop_table('course_grades')
    op.drop_table('courses')
    op.drop_table('students')
    op.drop_table('users')
    op.drop_table('tenants')
