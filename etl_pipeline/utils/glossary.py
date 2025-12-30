#!/usr/bin/env python

"""
Utilities for generating the course glossary
"""

def update_courses(courselist: list[dict], glossary: dict, inst: int) -> None:
    for course in courselist:
        if not all((course["prefix"],
                    course["courseNumber"],
                    course["courseTitle"],
                    course["minUnits"],
                    course["maxUnits"],
                    course["begin"])):
            continue
            
        course_id: int = course["courseIdentifierParentId"]
        
        if course_id not in glossary:            
            glossary[course_id] = {
                "course_id": course_id,
                "inst_id": int(inst),
                "course_code": f"{course["prefix"]} {course["courseNumber"]}",
                "course_name": course["courseTitle"],
                "min_units": int(course["minUnits"]),
                "max_units": int(course["maxUnits"]),
                "begin": course["begin"]
            }