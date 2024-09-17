from typing import List, Union

from beanie import PydanticObjectId

from models.admin import Admin
from models.student import Student
from models.analytic import Analytic

admin_collection = Admin
student_collection = Student
analytic_collection = Analytic


async def add_admin(new_admin: Admin) -> Admin:
    admin = await new_admin.create()
    return admin


async def retrieve_students() -> List[Student]:
    students = await student_collection.all().to_list()
    return students


async def add_student(new_student: Student) -> Student:
    student = await new_student.create()
    return student


async def retrieve_student(id: PydanticObjectId) -> Student:
    student = await student_collection.get(id)
    if student:
        return student


async def delete_student(id: PydanticObjectId) -> bool:
    student = await student_collection.get(id)
    if student:
        await student.delete()
        return True


async def update_student_data(id: PydanticObjectId, data: dict) -> Union[bool, Student]:
    des_body = {k: v for k, v in data.items() if v is not None}
    update_query = {"$set": {field: value for field, value in des_body.items()}}
    student = await student_collection.get(id)
    if student:
        await student.update(update_query)
        return student
    return False

async def add_analytic(new_analytic: Analytic) -> Analytic:
    analytic = await new_analytic.create()
    return analytic

async def retrieve_analytic(id: PydanticObjectId) -> Analytic:
    analytic = await analytic_collection.get(id)
    if analytic:
        return analytic

async def update_analytic_data(id: PydanticObjectId, data: dict) -> Union[bool, Analytic]:
    des_body = {k: v for k, v in data.items() if v is not None}
    update_query = {"$set": {field: value for field, value in des_body.items()}}
    analytic = await analytic_collection.get(id)
    if analytic:
        await analytic.update(update_query)
        return analytic
    return False