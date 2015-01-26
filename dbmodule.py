# -*- coding: utf-8 -*-
import sqlite3 as lite
import sys

def initSetup(dbname, categories):
  print("Creating Database: "+dbname)
  db = lite.connect(dbname)
  cursor = db.cursor()
  # Create Script Table
  cursor.execute('''
    create table scripts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL,
    author TEXT NULL)
  ''')
  print("Creating Table For Script ....")
  db.commit()
  # Create Categories Table
  cursor.execute('''create table categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
     name TEXT NOT NULL)
  ''')
  print("Creating Table for Categories .... ")
  db.commit()
  # Create Script/Category Table
  cursor.execute('''create table script_category(
    id_category INTEGER NOT NULL,
    id_script INETGER NOT NULL)
  ''')
  print("Creating Table for Scripts per Category ....")
  db.commit()
  print("Upload Categories to Categories Table ...")
  for category in categories:
    cursor.execute('''
      INSERT INTO categories (name) VALUES (?)
      ''',(category,))
    db.commit()
  db.close()

def insertScript(dbname,script):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute('''
    Insert into scripts (name) values (?)
    ''',(script,))
  db.commit()
  db.close()
  return cursor.lastrowid

def insertScriptCategory(dbname,scriptid,categoryid):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute('''
    Insert into script_category (id_category,id_script) values (?,?)
    ''',(categoryid,scriptid,))
  db.commit()
  db.close()

def searchScript(dbname,script):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select name from scripts where name like '%"+script+"%'")
  all_rows = cursor.fetchall()
  for row in all_rows:
    print('{0}'.format(row[0]))

def searchCategory(dbname,category):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select name from categories where name like '%"+category+"%'")
  all_rows = cursor.fetchall()
  for row in all_rows:
    print('{0}'.format(row[0]))