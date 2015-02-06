# -*- coding: utf-8 -*-
import sqlite3 as lite
import sys
import yaml

stream = open("config.yaml", 'r')
item = yaml.load(stream)

dbname = item["config"]["scriptdb"]
categories = item["config"]["categories"]
filePath = item["config"]["filePath"]
fileBackup = item["config"]["fileBackup"]
scriptsPath = item["config"]["scriptsPath"]
lastresults = {};

def initSetup():
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

def insertScript(script):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute('''
    Insert into scripts (name) values (?)
    ''',(script,))
  db.commit()
  db.close()
  return cursor.lastrowid

def insertScriptCategory(scriptid,categoryid):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute('''
    Insert into script_category (id_category,id_script) values (?,?)
    ''',(categoryid,scriptid,))
  db.commit()
  db.close()

def searchScript(script):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select name from scripts where name like '%"+script+"%'")
  return __fetchScript(cursor.fetchall())
  db.close()

def searchCategory(category):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.id=script_category.id_script and categories.id=script_category.id_category")
  return __fetchScript(cursor.fetchall())
  db.close()

def searchAll():
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select id, name from scripts ")
  return cursor.fetchall()
  db.close()

def __fetchScript(fetchall):
  i = 1
  fetchlist = {};
  for row in fetchall:
    fetchlist.update({i:row[0]})
    i = i+1
  return fetchlist