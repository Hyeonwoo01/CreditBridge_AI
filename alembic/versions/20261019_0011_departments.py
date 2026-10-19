"""departments table

ERD 검토(docs/ERD.md 6.1 E1) 반영. 학과를 글자 대신 행으로 둔다.
- departments(institution_id, name, UQ): 과목과 교수가 같은 학과 행을 가리켜야 자동 배정된다 (철자 차이 방지)
- courses.department(글자) → courses.department_id (NN FK), users.department(글자) → users.department_id (FK, null)
기존 글자 값으로 기관별 학과 행을 만들고 id로 옮긴 뒤 글자 컬럼을 지운다. 되돌리면 이름을 다시 글자로 채운다.
MySQL 8.0 호환 DDL·DML만 사용한다 (INSERT ... SELECT, UPDATE ... JOIN).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-19 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mariadb').with_variant(mysql.BIGINT(unsigned=True), 'mysql')
DT = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mariadb').with_variant(mysql.DATETIME(fsp=6), 'mysql')


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('institution_id', ID, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('id', ID, autoincrement=True, nullable=False),
        sa.Column('created_at', DT, nullable=False),
        sa.ForeignKeyConstraint(
            ['institution_id'], ['institutions.id'], name=op.f('fk_departments_institution_id_institutions')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
        sa.UniqueConstraint('institution_id', 'name', name=op.f('uq_departments_institution_id')),
    )
    # 과목과 교수(학과가 있는 사용자)의 학과명을 기관별로 한 행씩
    op.execute(
        """
        INSERT INTO departments (institution_id, name, created_at)
        SELECT institution_id, department, UTC_TIMESTAMP(6) FROM courses
        UNION
        SELECT institution_id, department, UTC_TIMESTAMP(6) FROM users
        WHERE institution_id IS NOT NULL AND department IS NOT NULL AND department <> ''
        """
    )

    op.add_column('courses', sa.Column('department_id', ID, nullable=True))
    op.execute(
        'UPDATE courses c JOIN departments d ON d.institution_id = c.institution_id AND d.name = c.department '
        'SET c.department_id = d.id'
    )
    op.alter_column('courses', 'department_id', existing_type=ID, nullable=False)
    op.create_foreign_key(
        op.f('fk_courses_department_id_departments'), 'courses', 'departments', ['department_id'], ['id']
    )
    op.create_index(op.f('ix_courses_department_id'), 'courses', ['department_id'], unique=False)
    op.drop_index(op.f('ix_courses_department'), table_name='courses')
    op.drop_column('courses', 'department')

    op.add_column('users', sa.Column('department_id', ID, nullable=True))
    op.execute(
        'UPDATE users u JOIN departments d ON d.institution_id = u.institution_id AND d.name = u.department '
        'SET u.department_id = d.id'
    )
    op.create_foreign_key(op.f('fk_users_department_id_departments'), 'users', 'departments', ['department_id'], ['id'])
    op.create_index(op.f('ix_users_department_id'), 'users', ['department_id'], unique=False)
    op.drop_index(op.f('ix_users_department'), table_name='users')
    op.drop_column('users', 'department')


def downgrade() -> None:
    op.add_column('users', sa.Column('department', sa.String(length=50), nullable=True))
    op.execute('UPDATE users u JOIN departments d ON d.id = u.department_id SET u.department = d.name')
    op.create_index(op.f('ix_users_department'), 'users', ['department'], unique=False)
    op.drop_constraint(op.f('fk_users_department_id_departments'), 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_department_id'), table_name='users')
    op.drop_column('users', 'department_id')

    op.add_column('courses', sa.Column('department', sa.String(length=50), nullable=True))
    op.execute('UPDATE courses c JOIN departments d ON d.id = c.department_id SET c.department = d.name')
    op.alter_column('courses', 'department', existing_type=sa.String(length=50), nullable=False)
    op.create_index(op.f('ix_courses_department'), 'courses', ['department'], unique=False)
    op.drop_constraint(op.f('fk_courses_department_id_departments'), 'courses', type_='foreignkey')
    op.drop_index(op.f('ix_courses_department_id'), table_name='courses')
    op.drop_column('courses', 'department_id')

    op.drop_table('departments')
