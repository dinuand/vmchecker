#! /usr/bin/python

from __future__ import with_statement
__author__ = 'Gheorghe Claudiu-Dan, claudiugh@gmail.com'

import sqlite3
import os
import time 
import stat 
import misc 

GRADE_VALUE_FILE = 'NOTA'

vmchk_root = os.path.abspath(misc.vmchecker_root())
db_path = misc.db_file()
cwd = os.getcwd()
checked_root = os.path.join(vmchk_root, 'checked')

if not cwd.startswith(checked_root):
    print "Error: working directory not in the VMCHECKER_ROOT subtree "
    exit()

if None == db_path:
    print "Error: DB file doesn't exist"
    exit()
    
db_conn = sqlite3.connect(db_path)
db_conn.isolation_level = None  # this is for autocommiting updates 
db_cursor = db_conn.cursor()

##################################################
#
#  DB routines  
# 

def DB_get_hw(hw_name):
    """ Get a homework entry 
    @return 
     - the id of the homework
     - None if it doesn't exist """
    global db_cursor
    db_cursor.execute('SELECT id FROM teme WHERE nume = ?;', (hw_name,))
    result = db_cursor.fetchone()
    if None == result:
        return result
    else:
        return result[0]

def DB_save_hw(hw_name):
    """ If the homework identified by (hw_name)  
    exists then update the DB, else insert a new entry """
    global db_cursor
    id_hw = DB_get_hw(hw_name)
    if None == id_hw:
        db_cursor.execute('INSERT INTO teme (nume) values (?)', (hw_name,))
        db_cursor.execute('SELECT last_insert_rowid();');
        (id_hw,) = db_cursor.fetchone()
        return id_hw
    else:
        return id_hw

def DB_get_student(student_name):
    """ Get a student entry 
    @return 
     - the id of the entry 
     - None if it doesn't exist """
    global db_cursor
    db_cursor.execute('SELECT id FROM studenti WHERE nume = ?;', (student_name,))
    result = db_cursor.fetchone()
    if None == result:
        return result
    else:
        return result[0]

def DB_save_student(student_name):
    """ If the student identified by (student_name)  
    exists then update the DB, else insert a new entry """
    global db_cursor
    id_student = DB_get_student(student_name)
    if None == id_student:
        db_cursor.execute('INSERT INTO studenti (nume) values (?)', (student_name,))
        db_cursor.execute('SELECT last_insert_rowid();');        
        (id_student,) = db_cursor.fetchone()
    return id_student

def DB_get_grade(id_hw, id_student):
    """ Get a grade entry 
    @return 
     - a touple containing the id and the last modification timestamp 
     - (None, None) if it doesn't exist """
    global db_cursor
    db_cursor.execute('SELECT id, data FROM note WHERE id_tema = ? and id_student = ?;', (id_hw, id_student))
    result = db_cursor.fetchone()
    if None == result:
        return (None, None)
    else:
        return result

def DB_save_grade(id_hw, id_student, grade, data):
    """ If the grade identified by (id_hw, id_student) 
    exists then update the DB, else insert a new entry """
    global db_cursor
    (id_grade, db_data) = DB_get_grade(id_hw, id_student)
    if None == id_grade:
        db_cursor.execute('INSERT INTO note (id_tema, id_student, nota, data) values (?, ?, ?, ?)', (id_hw, id_student, grade, data ))
    else:       
        db_cursor.execute('UPDATE note set nota = ?, data = ? where id = ?', (grade, data, id_grade))

#        
#################################################

def update_hws(path):
    """ For each dentry from path, launch the next 
    level update routine - update_students() """
    for hw_name in os.listdir(path):
        path_hw = os.path.join(path, hw_name)        
        mode = os.stat(path_hw)[stat.ST_MODE]
        if stat.S_ISDIR(mode):        
            # save hw in the DB
            id_hw = DB_save_hw(hw_name)
            #print hw_name
            update_students(path_hw, id_hw)

def update_students(path, id_hw):
    """ For each dentry from path, 
    launch the update_grade() routine"""
    for student_name in os.listdir(path):
        path_student = os.path.join(path, student_name)        
        mode = os.stat(path_student)[stat.ST_MODE]
        if stat.S_ISDIR(mode):        
            # save student in the DB
            id_student = DB_save_student(student_name)
            #print "\t ", student_name,
            update_grade(path_student, id_hw, id_student)

def grade_modification_time(grade_filename):
    return time.strftime("%Y-%m-%d %H-%M-%S", time.gmtime(os.path.getmtime(grade_filename)))

def get_grade_value(grade_filename):
    """ read an integer from the first line of the file """
    with open(grade_filename, 'r') as f:
        value = int(f.read())
    return value
    
def update_grade(path, id_hw, id_student):
    """ Reads the grade's value only if the file containing the
    value was modified since the last update of the DB for this
    submission. """
    grade_filename = os.path.join(path, GRADE_VALUE_FILE)
    if not os.path.exists(grade_filename):
        print "Error. File ", grade_filename, " for grade value does not exist "
        return None
    data_modif = grade_modification_time(grade_filename)
    (id_grade, db_data) = DB_get_grade(id_hw, id_student)
    if db_data != data_modif:
        # modified since last db save 
        grade_value = get_grade_value(grade_filename)
        if None != grade_value:        
            # update information from DB
            DB_save_grade(id_hw, id_student, grade_value, data_modif)
            print path, " UPDATED "
#    else:
#        print " "

def main():
    # determine the level 
    LEVEL_HWS = 0
    LEVEL_STUDENTI = 1
    LEVEL_GRADE = 2

    path = cwd
    level = LEVEL_HWS
    while path != checked_root:    
        (path, tail) = os.path.split(path)
        level = level + 1

    if level == LEVEL_HWS:
        update_hws(cwd)
    elif level == LEVEL_STUDENTI:
        # get the name for homework
        (head, nume_hw) = os.path.split(cwd)
        # get the id 
        id_hw = DB_save_hw(nume_hw)
        update_students(cwd, id_hw)
    elif level == LEVEL_GRADE:
        # get the  names from the path 
        (head, nume_student) = os.path.split(cwd)
        (head, nume_hw) = os.path.split(head)
        # get the DB identifiers 
        id_hw = DB_save_hw(nume_hw)
        id_student = DB_save_student(nume_student)
        update_grade(cwd, id_hw, id_student)

        db_cursor.close() 
        db_conn.close() 


if __name__ == '__main__':
    main()