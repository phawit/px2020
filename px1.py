#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# import pyzbar.pyzbar as pyzbar
import numpy as np
# import cv2
from collections import Counter
import time
import csv
import json
import datetime
import os

from evdev import InputDevice, ecodes, list_devices
from select import select

from threading import Thread, Lock

import firebase_admin
from firebase_admin import credentials, db

import pyxhook

cred = credentials.Certificate('db/serviceAccountKey.json')
firebase_default_app = firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://testjson-807aa.firebaseio.com'
})

# Get a database reference to our blog.
firebase_ref = db.reference('/')
users_ref = firebase_ref.child('data')

Ui_MainWindow, QtBaseClass = uic.loadUiType('ui/main.ui')
Ui_AddWindow, QtBaseClass = uic.loadUiType('ui/add.ui')
Ui_StockWindow, QtBaseClass = uic.loadUiType('ui/stock.ui')
Ui_AddStockWindow, QtBaseClass = uic.loadUiType('ui/addStock.ui')
Ui_ChangePriceWindow, QtBaseClass = uic.loadUiType('ui/changePrice.ui')
Ui_FinishWindow, QtBaseClass = uic.loadUiType('ui/finish.ui')
Ui_DateInfoWindow, QtBaseClass = uic.loadUiType('ui/date_info.ui')
Ui_DateHistoryWindow, QtBaseClass = uic.loadUiType('ui/date_log.ui')
Ui_EditDetailWindow, QtBaseClass = uic.loadUiType('ui/editDetail.ui')
Ui_ShortcutWindow, QtBaseClass = uic.loadUiType('ui/shortcut_grid_edit.ui')
Ui_EditUnitsTableWindow, QtBaseClass = uic.loadUiType('ui/edit_units_in_table.ui')
Ui_StockHistoryWindow, QtBaseClass = uic.loadUiType('ui/stock_log.ui')
Ui_DepWitWindow, QtBaseClass = uic.loadUiType('ui/drawer_dep_wit.ui')
Ui_DrawerHistoryWindow, QtBaseClass = uic.loadUiType('ui/drawer_history.ui')

date_data = {}
history_data = {}

template_history = {
                    'Total Price': 0,
                    'Price': {},
                    'Items': {}
}

template_json = {u'20180101': 
            {u'Changed Price': {},
            u'Daily Sales': 0.0,
            u'Item Sales': {},
            u'Stock Adding': {},
            u'Current Stock': {}}
        }

items_list = []

items_info = {'Barcode':'000',
              'Item Name':'000',
              'Price':'000',
              'Unit':'000',
              'Total':'000',
              'Stock':'000'}

def merge(d1, d2, merge_fn=lambda x,y:y):
    """
    Merges two dictionaries, non-destructively, combining 
    values on duplicate keys as defined by the optional merge
    function.  The default behavior replaces the values in d1
    with corresponding values in d2.  (There is no other generally
    applicable merge strategy, but often you'll have homogeneous 
    types in your dicts, so specifying a merge technique can be 
    valuable.)

    Examples:

    >>> d1
    {'a': 1, 'c': 3, 'b': 2}
    >>> merge(d1, d1)
    {'a': 1, 'c': 3, 'b': 2}
    >>> merge(d1, d1, lambda x,y: x+y)
    {'a': 2, 'c': 6, 'b': 4}

    """
    result = dict(d1)
    for k,v in d2.iteritems():
        if k in result:
            result[k] = merge_fn(result[k], v)
        else:
            result[k] = v
    return result

def FirebaseUpdate():
    monthly = 0.0
    daily = 0.0
    month_str = datetime.datetime.now().strftime("%Y%m")
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    date_time_str = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
    
    for k, v in date_data.iteritems():
        if str(k[:6]) == month_str:
            monthly += v[u"Daily Sales"]

        if str(k) == date_str:
            daily = v[u"Daily Sales"]

    try:
        users_ref.update({
            'Daily': daily,
            'Monthly': monthly,
            'Drawer': date_data['Drawer']['Money'],
            'Last Modified': date_time_str
        })
    except:
        print("No internet connection")

def UpdateJSON(key, value):
    print 'upjsonnnnnnnnnnnnnnnnnnnnnnnnnn'
    # -----------------------------------------------
    # with open('db/data.json') as f:
    #     date_data = json.load(f)

    
    # -----------------------------------------------




    date_str = datetime.datetime.now().strftime("%Y%m%d")
    if date_str in date_data:
        pass
    else:
        for k, v in template_json.iteritems():
            old_key = k
        template_json[date_str] = template_json.pop(old_key)
        date_data[unicode(date_str, "utf-8")] = template_json.pop(date_str)

    if key == 'sell':
        print 'selllll'
        date_data[date_str][u'Daily Sales'] += value[2]
        date_data['Drawer']['Money'] += value[2]
        if value[0] in date_data[date_str][u'Item Sales']:
            date_data[date_str][u'Item Sales'][value[0]] = value[1] + date_data[date_str][u'Item Sales'][value[0]]
        else:
            date_data[date_str][u'Item Sales'][value[0]] = value[1]
    elif key == 'stock':
        if u'Stock Adding' in date_data[date_str]:
            pass
        else:
            date_data[date_str][u'Stock Adding'] = {}
        date_time_str = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
        date_data[date_str][u'Stock Adding'][date_time_str] = {}
        date_data[date_str][u'Stock Adding'][date_time_str][value[0]] = value[1]
    elif key == 'change':
        if u'Changed Price' in date_data[date_str]:
            pass
        else:
            date_data[date_str][u'Changed Price'] = {}

        date_time_str = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
        date_data[date_str][u'Changed Price'][date_time_str] = {}
        date_data[date_str][u'Changed Price'][date_time_str]['Barcode'] = value[0]
        date_data[date_str][u'Changed Price'][date_time_str]['From'] = value[1]
        date_data[date_str][u'Changed Price'][date_time_str]['To'] = value[2]
    elif key == 'none':
        pass

    # ------------------------------------------------
    print 'ooooooooooooooooooooooooooooooooo'
    items_list = []
    with open('db/ItemList.csv','r') as f:
        print f
        for line in f:
            print line
            line_split = line.strip().split(',')
            (barcode,name,price,stock) = line_split
            items = items_info.copy()
            items['Barcode'] = barcode
            items['Item Name'] = unicode(name, "utf-8")
            items['Price'] = price
            items['Stock'] = stock
            # print items
            items_list.append(items)
            
            print 'iiiiiiiiiiiii'
            print items['Stock']
    # ---------------------------------------------------------

    for items in items_list:
        print 'tttttttttttt'
        print int(items['Stock'])
        date_data[date_str][u'Current Stock'][unicode(items['Barcode'], "utf-8")] = int(items['Stock'])

    with open('db/data.json', 'w') as fp:
        json.dump(date_data, fp, sort_keys=True, indent=4, separators=(',', ': '))

    ft.firebase_update = True

image_viewer_size = (280,210)

class firebase_thread:
    def __init__(self) :
        self.started = False
        self.firebase_update = False

    def start(self) :
        print 'fb thread START'
        if self.started :
            print("already started!!")
            return None
        self.started = True
        self.thread = Thread(target=self.run, args=())
        self.thread.start()
        
        return self

    def run(self):
        while self.started:
            time.sleep(60)
            FirebaseUpdate()

class Barcode_process:
    def __init__(self) :
        self.started = False
        self.barcode = []
        self.barcode_tmp = ""

        self.new_hook=pyxhook.HookManager()
        #listen to all keystrokes
        self.new_hook.KeyDown=self.OnKeyPress
        #hook the keyboard
        self.new_hook.HookKeyboard()
        #start the session
        self.new_hook.start()
        
    def OnKeyPress(self, event):
        if event.Key == 'Return':
            if len(self.barcode_tmp) == 13:
                self.barcode.append(self.barcode_tmp)
                # print(self.barcode)
            self.barcode_tmp = ""
        else:
            self.barcode_tmp += event.Key

class Stock_window(QtGui.QDialog, Ui_StockWindow):
    def __init__(self, parent=None):
        
        super(Stock_window, self).__init__(parent)
        self.setupUi(self)

        self.selectedRow = -1
        self.table_stock.clicked.connect(self.updateSelected)

        self.addstock_app = AddStock_window(self)
        self.changeprice_app = ChangePrice_window(self)
        self.stockhistory_app = StockHistory_window(self)
        self.addStock_button.clicked.connect(self.addStock)
        self.editPrice_button.clicked.connect(self.changePrice)
        self.history_button.clicked.connect(self.OpenStockHistory)
        self.remove_button.clicked.connect(self.removeItems)

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_stock.setHorizontalHeaderLabels(header)
        header = self.table_stock.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)

        # ----------------------------------------------
        with open('db/data.json') as f:
            date_data = json.load(f)

        items_list = []
        with open('db/ItemList.csv','r') as f:
            print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                # print items
                items_list.append(items)


        #--------------------------------------------------

        for items in items_list:
            if int(items['Stock']) > -1:
                item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                r = self.table_stock.rowCount()
                self.table_stock.insertRow(r)
                for i in range(len(item_array)):
                    self.table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                    if i > 1:
                        self.table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.table_stock.sortItems(1)

    def removeItems(self):
        if self.selectedRow > -1:
            barcode = str(self.table_stock.item(self.selectedRow, 0).text())

            for ii in range(len(items_list)):
                items = items_list[ii]
                if barcode == items['Barcode']:
                    UpdateJSON('stock', [barcode, -int(items['Stock'])])
                    items['Stock'] = '-1'
                    # del items_list[ii]

            file = open('db/ItemList.csv','w')
            fcsv = csv.writer(file, lineterminator='\n')
            for items in items_list:
                info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
                fcsv.writerow(info)
            file.close()
            UpdateJSON('none', [])

            r = self.table_stock.rowCount()
            while r > 0:
                self.table_stock.removeRow(r-1)
                r = self.table_stock.rowCount()
            self.table_stock.setSortingEnabled(False)
            for items in items_list:
                if int(items['Stock']) > -1:
                    item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                    r = self.table_stock.rowCount()
                    self.table_stock.insertRow(r)
                    for i in range(len(item_array)):
                        self.table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            self.table_stock.setSortingEnabled(True)
            self.table_stock.sortItems(1)

    def OpenStockHistory(self):
        del self.stockhistory_app
        self.stockhistory_app = StockHistory_window(self)
        self.stockhistory_app.show()
        self.stockhistory_app.activateWindow()

    def addStock(self):
        self.addstock_app.line_barcode.setText('')
        self.addstock_app.line_name.setText('')
        self.addstock_app.line_price.setText('')
        self.addstock_app.line_units.setText('')
        self.addstock_app.line_barcode.setFocus(True)
        self.addstock_app.show()
        self.addstock_app.activateWindow()

    def changePrice(self):
        self.changeprice_app.line_barcode.setText('')
        self.changeprice_app.line_name.setText('')
        self.changeprice_app.line_price.setText('')
        self.changeprice_app.line_new_price.setText('')
        self.changeprice_app.show()
        self.changeprice_app.activateWindow()

    def updateSelected(self):
        self.selectedRow = self.table_stock.currentRow()

class StockHistory_window(QtGui.QDialog, Ui_StockHistoryWindow):
    def __init__(self, parent=None):
        print 'Stock his window'
        super(StockHistory_window, self).__init__(parent)
        self.setupUi(self)

        self.table_addstock.cellClicked.connect(self.show_detail)
        # self.add_button.clicked.connect(self.add_detail)
        self.remove_button.clicked.connect(self.remove_detail)
        self.edit_button.clicked.connect(self.edit_detail)

        self.selectedRow_sales = -1
        self.table_addstock.clicked.connect(self.updateSelected_sales)
        self.selectedRow_detail = -1
        self.table_detail.clicked.connect(self.updateSelected_detail)

        header = ['วันที่-เวลา']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_addstock.setHorizontalHeaderLabels(header)
        header = self.table_addstock.horizontalHeader()
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)

        with open('db/data.json') as f:
            date_data = json.load(f)

        for key, value in date_data.iteritems():
            if key == 'Drawer':
                continue

            for kk, vv in date_data[key][u'Stock Adding'].iteritems():
                r = self.table_addstock.rowCount()
                self.table_addstock.insertRow(r)
                self.table_addstock.setItem(r , 0, QtGui.QTableWidgetItem(str(kk)))

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_detail.setHorizontalHeaderLabels(header)
        header = self.table_detail.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(4, QtGui.QHeaderView.ResizeToContents)

        self.table_addstock.sortItems(0, Qt.DescendingOrder)

    def RefreshTable(self):
        self.table_addstock.setSortingEnabled(False)
        self.table_detail.setSortingEnabled(False)
        r = self.table_detail.rowCount()
        while r > 0:
            self.table_detail.removeRow(r-1)
            r = self.table_detail.rowCount()
        self.table_detail.clearSelection()

        r = self.table_addstock.rowCount()
        while r > 0:
            self.table_addstock.removeRow(r-1)
            r = self.table_addstock.rowCount()
        self.table_addstock.clearSelection()

        header = ['วันที่-เวลา']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_addstock.setHorizontalHeaderLabels(header)
        header = self.table_addstock.horizontalHeader()
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        for key, value in date_data.iteritems():
            if key == 'Drawer':
                continue
                
            for kk, vv in date_data[key][u'Stock Adding'].iteritems():
                r = self.table_addstock.rowCount()
                self.table_addstock.insertRow(r)
                self.table_addstock.setItem(r , 0, QtGui.QTableWidgetItem(str(kk)))
        
        UpdateJSON('none', [])
        self.table_addstock.setSortingEnabled(True)
        self.table_detail.setSortingEnabled(True)

        self.parent().table_stock.setSortingEnabled(False)
        r = self.parent().table_stock.rowCount()
        while r > 0:
            self.parent().table_stock.removeRow(r-1)
            r = self.parent().table_stock.rowCount()

        for items in items_list:
            if int(items['Stock']) > -1:
                item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                r = self.parent().table_stock.rowCount()
                self.parent().table_stock.insertRow(r)
                for i in range(len(item_array)):
                    self.parent().table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                    if i > 1:
                        self.parent().table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.parent().table_stock.sortItems(1)

    def show_detail(self):
        print 'show de'
        # ----------------------------------------------
        with open('db/data.json') as f:
            date_data = json.load(f)
        #--------------------------------------------------

        row = self.table_addstock.currentRow()
        detail = str(self.table_addstock.item(row, 0).text())
        date = detail.strip().split('-')[0]

        self.table_detail.setSortingEnabled(False)
        r = self.table_detail.rowCount()
        while r > 0:
            self.table_detail.removeRow(r-1)
            r = self.table_detail.rowCount()

        for key, value in date_data[date][u'Stock Adding'][detail].iteritems():
            r = self.table_detail.rowCount()
            self.table_detail.insertRow(r)

            barcode = str(key)
            units = str(value)
            name = ''
            price = ''
            for items in items_list:
                if items['Barcode'] == barcode:
                    price = items['Price']
                    name = items['Item Name']

            self.table_detail.setItem(r , 0, QtGui.QTableWidgetItem(barcode))
            self.table_detail.setItem(r , 1, QtGui.QTableWidgetItem(name))
            self.table_detail.setItem(r , 2, QtGui.QTableWidgetItem(price))
            self.table_detail.item(r, 2).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            self.table_detail.setItem(r , 3, QtGui.QTableWidgetItem(units))
            self.table_detail.item(r, 3).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.table_detail.setSortingEnabled(True)
        self.table_detail.sortItems(1)

    def add_detail(self):
        self.edit_app = EditDetail_window(self, action='add')
        self.edit_app.show()
        self.edit_app.activateWindow()

    def remove_detail(self):
        global date_data

        detail = str(self.table_addstock.item(self.selectedRow_sales, 0).text())
        date = detail.strip().split('-')[0]
        barcode = str(self.table_detail.item(self.selectedRow_detail,0).text())

        file = open('db/ItemList.csv','w')
        fcsv = csv.writer(file, lineterminator='\n')
        for items in items_list:
            if items['Barcode'] == str(barcode):
                print 'stock : '
                print int(items['Stock'])
                print 'remove : '
                print date_data[date][u'Stock Adding'][detail][unicode(barcode)]
                print date_data[date][u'Stock Adding'][detail][unicode(barcode)]

                if int(items['Stock']) == -1:
                    items['Stock'] = str(0 - date_data[date][u'Stock Adding'][detail][unicode(barcode)])
                else:
                    items['Stock'] = str(int(items['Stock']) - date_data[date][u'Stock Adding'][detail][unicode(barcode)])

                
                

            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            fcsv.writerow(info)
        file.close()

        del date_data[date][u'Stock Adding'][detail][unicode(barcode)]
        UpdateJSON('none', [])

        self.RefreshTable()
        
    def edit_detail(self):
        self.edit_app = EditStockHistory_window(self, action='edit')
        self.edit_app.show()
        self.edit_app.activateWindow()

    def updateSelected_sales(self):
        self.selectedRow_sales = self.table_addstock.currentRow()
    def updateSelected_detail(self):
        self.selectedRow_detail = self.table_detail.currentRow()

class EditStockHistory_window(QtGui.QDialog, Ui_EditDetailWindow):
    def __init__(self, parent=None, action='add'):
        super(EditStockHistory_window, self).__init__(parent)
        self.setupUi(self)

        self.action = action

        self.onlydouble = QDoubleValidator()
        self.onlyint = QIntValidator()
        self.line_price.setValidator(self.onlydouble)
        self.line_units.setValidator(self.onlyint)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateInfo)
        self.timer.start(500)
        self.row = -1

        self.edit_button.clicked.connect(self.EditDetail)
        self.line_barcode.textChanged.connect(self.BarcodeChange)

        self.line_barcode.setFocus(True)

        if action == 'add':
            self.edit_button.setText(u'เพิ่ม')
        else:
            self.edit_button.setText(u'แก้ไข')

    def BarcodeChange(self):
        for items in items_list:
            if self.line_barcode.text() == items['Barcode']:
                self.line_name.setText(items['Item Name'])
                self.line_price.setText(items['Price'])

    def EditDetail(self):
        global date_data
        detail = str(self.parent().table_addstock.item(self.parent().selectedRow_sales, 0).text())
        date = detail.strip().split('-')[0]
        barcode = self.line_barcode.text()
        new_units = int(self.line_units.text())
        if self.action == 'edit':
            file = open('db/ItemList.csv','w')
            fcsv = csv.writer(file, lineterminator='\n')
            for items in items_list:
                if items['Barcode'] == str(barcode):
                    items['Stock'] = str(int(items['Stock']) - date_data[date][u'Stock Adding'][detail][unicode(barcode)] + new_units)
                info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
                fcsv.writerow(info)
            file.close()

            date_data[date][u'Stock Adding'][detail][unicode(barcode)] = new_units

            UpdateJSON('none', [])
        
        self.parent().RefreshTable()
        self.parent().selectedRow_detail = -1
        self.close()

    def updateInfo(self):
        if self.action == 'edit':
            if self.parent().selectedRow_detail > -1:
                self.row = self.parent().selectedRow_detail
                self.line_barcode.setText(self.parent().table_detail.item(self.row, 0).text())
                self.line_name.setText(self.parent().table_detail.item(self.row, 1).text())
                self.line_price.setText(self.parent().table_detail.item(self.row, 2).text())
                # self.line_units.setText(self.parent().table_detail.item(self.row, 3).text())

class ChangePrice_window(QtGui.QDialog, Ui_ChangePriceWindow):
    def __init__(self, parent=None):
        super(ChangePrice_window, self).__init__(parent)
        self.setupUi(self)

        self.onlydouble = QDoubleValidator()
        self.line_price.setValidator(self.onlydouble)
        self.line_new_price.setValidator(self.onlydouble)
        self.line_barcode.setFocus(True)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateInfo)
        self.timer.start(1000)
        self.row = -1

        self.change_button.clicked.connect(self.ChangePrice)
        self.line_barcode.textChanged.connect(self.BarcodeChange)

    def BarcodeChange(self):
        for items in items_list:
            if self.line_barcode.text() == items['Barcode']:
                self.line_name.setText(items['Item Name'])
                self.line_price.setText(items['Price'])

    def WriteTable2CSV(self):
        file = open('db/ItemList.csv','w')
        fcsv = csv.writer(file, lineterminator='\n')
        for items in items_list:
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            fcsv.writerow(info)
        file.close()
        UpdateJSON('none', [])

    def ChangePrice(self):
        global items_list
        inList = False
        for items in items_list:
            if items['Barcode'] == str(self.line_barcode.text()):
                inList = True
                break

        if str(self.line_new_price.text()) != "":
            if inList:
                for ii in range(len(items_list)):
                    items = items_list[ii]
                    if items['Barcode'] == str(self.line_barcode.text()):
                        UpdateJSON('change', [items['Barcode'], items['Price'], "{:.2f}".format(float(self.line_new_price.text()) )])
                        items['Price'] = "{:.2f}".format(float(self.line_new_price.text()) )
                    items_list[ii] = items
            
                self.WriteTable2CSV()

                self.parent().table_stock.setSortingEnabled(False)
                r = self.parent().table_stock.rowCount()
                while r > 0:
                    self.parent().table_stock.removeRow(r-1)
                    r = self.parent().table_stock.rowCount()

                for items in items_list:
                    if int(items['Stock']) > -1:
                        item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                        r = self.parent().table_stock.rowCount()
                        self.parent().table_stock.insertRow(r)
                        for i in range(len(item_array)):
                            self.parent().table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                            if i > 1:
                                self.parent().table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                self.parent().table_stock.setSortingEnabled(True)
            self.parent().parent().refresh_shortcut_button()
            self.close()

    def updateInfo(self):
        if self.parent().selectedRow > -1:
            self.row = self.parent().selectedRow
            self.line_barcode.setText(self.parent().table_stock.item(self.row, 0).text())
            self.line_name.setText(self.parent().table_stock.item(self.row, 1).text())
            self.line_price.setText(self.parent().table_stock.item(self.row, 2).text())

class AddStock_window(QtGui.QDialog, Ui_AddStockWindow):
    def __init__(self, parent=None):
        super(AddStock_window, self).__init__(parent)
        self.setupUi(self)


        






        self.onlydouble = QDoubleValidator()
        self.onlyint = QIntValidator()
        self.line_price.setValidator(self.onlydouble)
        self.line_units.setValidator(self.onlyint)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateInfo)
        self.timer.start(1000)
        self.row = -1

        self.add_button.clicked.connect(self.AddStock)
        self.line_barcode.textChanged.connect(self.BarcodeChange)

    def BarcodeChange(self):
        for items in items_list:
            if self.line_barcode.text() == items['Barcode']:
                self.line_name.setText(items['Item Name'])
                self.line_price.setText(items['Price'])

    def WriteTable2CSV(self):
        file = open('db/ItemList.csv','w')
        fcsv = csv.writer(file, lineterminator='\n')
        for items in items_list:
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            fcsv.writerow(info)
        file.close()
        UpdateJSON('none', [])
        

    def AddStock(self):
        global items_list
        if str(self.line_units.text()) == '':
            pass
        else:
            self.parent().table_stock.setSortingEnabled(False)
            inList = False
            out_of_stock = False




            items_list = []
            with open('db/ItemList.csv','r') as f:
                print f
                for line in f:
                    print line
                    line_split = line.strip().split(',')
                    (barcode,name,price,stock) = line_split
                    items = items_info.copy()
                    items['Barcode'] = barcode
                    items['Item Name'] = unicode(name, "utf-8")
                    items['Price'] = price
                    items['Stock'] = stock
                    # print items
                    items_list.append(items)




            for items in items_list:
                if items['Barcode'] == str(self.line_barcode.text()):
                    if int(items['Stock']) == -1:
                        out_of_stock = True
                        items['Stock'] = '0'
                    inList = True
                    break
            
            if inList:
                if out_of_stock:
                    r = self.parent().table_stock.rowCount()
                    while r > 0:
                        self.parent().table_stock.removeRow(r-1)
                        r = self.parent().table_stock.rowCount()

                    for items in items_list:
                        if int(items['Stock']) > -1:
                            item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                            r = self.parent().table_stock.rowCount()
                            self.parent().table_stock.insertRow(r)
                            for i in range(len(item_array)):
                                self.parent().table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                                if i > 1:
                                    self.parent().table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

                for ii in range(len(items_list)):
                    items = items_list[ii]
                    if items['Barcode'] == str(self.line_barcode.text()):
                        for rr in range(self.parent().table_stock.rowCount()):
                            if str(self.line_barcode.text()) == str(self.parent().table_stock.item(rr, 0).text()):
                                num_stock = int(str(self.parent().table_stock.item(rr, 3).text())) + int(str(self.line_units.text()))
                                self.parent().table_stock.setItem(rr, 3, QtGui.QTableWidgetItem(str(num_stock)))
                                self.parent().table_stock.item(rr, 3).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                                items['Stock'] = str(num_stock)
                                UpdateJSON('stock', [items['Barcode'], int(str(self.line_units.text()))])
                    items_list[ii] = items
            else:
                items = items_info.copy()
                items['Barcode'] = str(self.line_barcode.text())
                items['Item Name'] = unicode(self.line_name.text())
                items['Price'] = "{:.2f}".format(float(self.line_price.text()) )
                items['Stock'] = str(self.line_units.text())
                items_list.append(items)
                UpdateJSON('stock', [items['Barcode'], int(str(self.line_units.text()))])
            
            self.WriteTable2CSV()

            r = self.parent().table_stock.rowCount()
            while r > 0:
                self.parent().table_stock.removeRow(r-1)
                r = self.parent().table_stock.rowCount()

            for items in items_list:
                if int(items['Stock']) > -1:
                    item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
                    r = self.parent().table_stock.rowCount()
                    self.parent().table_stock.insertRow(r)
                    for i in range(len(item_array)):
                        self.parent().table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.parent().table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            self.parent().table_stock.setSortingEnabled(True)
            self.parent().table_stock.sortItems(1)
            self.parent().selectedRow = -1
            self.close()

    def updateInfo(self):
        if self.parent().selectedRow > -1:
            self.row = self.parent().selectedRow
            self.line_barcode.setText(self.parent().table_stock.item(self.row, 0).text())
            self.line_name.setText(self.parent().table_stock.item(self.row, 1).text())
            self.line_price.setText(self.parent().table_stock.item(self.row, 2).text())

class Add_window(QtGui.QDialog, Ui_AddWindow):
    print 'Add Window..................................'
    def __init__(self, parent=None):
        print 'Add window init'
        super(Add_window, self).__init__(parent)
        self.setupUi(self)
        self.add_button.clicked.connect(self.AddItem)
        self.line_barcode.textChanged.connect(self.BarcodeChange)
        self.line_barcode.setFocus(True)

        self.onlydouble = QDoubleValidator()
        self.onlyint = QIntValidator()
        self.line_price.setValidator(self.onlydouble)
        self.line_units.setValidator(self.onlyint)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateInfo)
        self.timer.start(1000)
        self.row = -1

    def updateInfo(self):
        # print 'Add window updateInfo'
        if self.parent().selectedRow > -1:
            self.row = self.parent().selectedRow
            if str(self.parent().table.item(self.row, 0).text()) != '':
                self.line_barcode.setText(self.parent().table.item(self.row, 0).text())
                self.line_name.setText(self.parent().table.item(self.row, 1).text())
                self.line_price.setText(self.parent().table.item(self.row, 2).text())

    def BarcodeChange(self):
        print 'Add window.BarcodeChange'
        for items in items_list:
            if self.line_barcode.text() == items['Barcode']:
                self.line_name.setText(items['Item Name'])
                self.line_price.setText(items['Price'])

    def AddItem(self):
        print 'Add window.AddItem'
        if str(self.line_units.text()) != '':
            items_info['Barcode'] = str(self.line_barcode.text())

            inList = False
            for items in items_list:
                if items['Barcode'] == str(self.line_barcode.text()):
                    inList = True
                    break

            if inList:
                items_info['Item Name'] = self.line_name.text()
                items_info['Price'] = "{:.2f}".format(float(self.line_price.text()) )
                items_info['Unit'] = str(self.line_units.text())
                try:
                    items_info['Total'] = "{:.2f}".format( int(items_info['Unit'])*float(items_info['Price']) )
                except:
                    items_info['Total'] = "{:.2f}".format(0.00)

                # check duplicate in table
                r = self.parent().table.rowCount()
                isDuplicate = -1
                for row in range(r):
                    if self.parent().table.item(row, 0).text() == items_info['Barcode']:
                        isDuplicate = row
                        num_unit = int(items_info['Unit']) + int(self.parent().table.item(row, 3).text())
                        items_info['Unit'] = str(num_unit)
                        items_info['Total'] = "{:.2f}".format( int(items_info['Unit'])*float(items_info['Price']) )

                item_array = [items_info['Barcode'], items_info['Item Name'], items_info['Price'], items_info['Unit'], items_info['Total']]
                if isDuplicate == -1:
                    self.parent().table.insertRow(r)
                    for i in range(len(item_array)):
                        self.parent().table.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.parent().table.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                else:
                    row = isDuplicate
                    for i in range(len(item_array)):
                        self.parent().table.setItem(row , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.parent().table.item(row, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                r = self.parent().table.rowCount()
                total_price = 0.0
                for row in range(r):
                    total_price += float(self.parent().table.item(row, 4).text())
                self.parent().total_price.setText("{:.2f}".format(total_price))
                self.parent().total_price.setAlignment(QtCore.Qt.AlignRight)
                self.timer.stop()
            self.parent().selectedRow = -1
            self.close()
 
class DateInfo_window(QtGui.QDialog, Ui_DateInfoWindow):
    def __init__(self, parent=None):
        print 'ddddddddd'
        super(DateInfo_window, self).__init__(parent)
        self.setupUi(self)
        self.history_button.clicked.connect(self.OpenHistoryApp)

    def OpenHistoryApp(self):
        print 'hhhhhhh'
        self.history_app = DateHistory_window(self)
        self.history_app.show()
        self.history_app.activateWindow()

        self.close()

class DateHistory_window(QtGui.QDialog, Ui_DateHistoryWindow):
    def __init__(self, parent=None):
        
        super(DateHistory_window, self).__init__(parent)
        self.setupUi(self)

        self.table_sales.cellClicked.connect(self.show_detail)
        self.add_button.clicked.connect(self.add_detail)
        self.remove_button.clicked.connect(self.remove_detail)
        self.edit_button.clicked.connect(self.edit_detail)

        self.selectedRow_sales = -1
        self.table_sales.clicked.connect(self.updateSelected_sales)
        self.selectedRow_detail = -1
        self.table_detail.clicked.connect(self.updateSelected_detail)

        date_str = str(self.parent().parent().date.toString('yyyy-MM-dd'))
        data_str = 'ประวัติรายการประจำวันที่ ' + date_str
        data_str = unicode(data_str, 'utf-8')
        self.label_date.setText(data_str)

        date_str = str(self.parent().parent().date.toString('yyyyMMdd'))
        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")

        # ----------------------------------------------------
        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        print curr_date_str

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
            history_data = json.loads(json_data)

            self.history_data = history_data

        # ---------------------------------------------------------

        if curr_date_str != date_str:
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            json_data=open('db/history/' + date_str + '.json').read()
            self.history_data = json.loads(json_data)
        else:
            
            self.history_data = history_data

        header = ['วันที่-เวลา', 'ยอดขาย']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_sales.setHorizontalHeaderLabels(header)
        header = self.table_sales.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        for key, value in self.history_data.iteritems():
            r = self.table_sales.rowCount()
            self.table_sales.insertRow(r)
            self.table_sales.setItem(r , 0, QtGui.QTableWidgetItem(str(key)))
            self.table_sales.setItem(r , 1, QtGui.QTableWidgetItem("{:.2f}".format(self.history_data[key][u'Total Price'])))
            self.table_sales.item(r, 1).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        
        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน', 'ราคารวม']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_detail.setHorizontalHeaderLabels(header)
        header = self.table_detail.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(4, QtGui.QHeaderView.ResizeToContents)

        self.table_sales.sortItems(0, Qt.DescendingOrder)
    
    def RefreshTable(self):
        self.parent().parent().ShowCalendarInfo(self.parent().parent().date)
        self.table_sales.setSortingEnabled(False)
        self.table_detail.setSortingEnabled(False)
        r = self.table_detail.rowCount()
        while r > 0:
            self.table_detail.removeRow(r-1)
            r = self.table_detail.rowCount()
        self.table_detail.clearSelection()

        r = self.table_sales.rowCount()
        while r > 0:
            self.table_sales.removeRow(r-1)
            r = self.table_sales.rowCount()
        self.table_sales.clearSelection()

        header = ['วันที่-เวลา', 'ยอดขาย']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_sales.setHorizontalHeaderLabels(header)
        header = self.table_sales.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        for key, value in history_data.iteritems():
            r = self.table_sales.rowCount()
            self.table_sales.insertRow(r)
            self.table_sales.setItem(r , 0, QtGui.QTableWidgetItem(str(key)))
            self.table_sales.setItem(r , 1, QtGui.QTableWidgetItem("{:.2f}".format(history_data[key][u'Total Price'])))
            self.table_sales.item(r, 1).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        
        UpdateJSON('none', [])
        date_str = str(self.parent().parent().date.toString('yyyyMMdd'))
        with open('db/history/'+date_str + '.json', 'w') as fp:
            json.dump(history_data, fp, sort_keys=True, indent=4, separators=(',', ': '))
        self.table_sales.setSortingEnabled(True)
        self.table_detail.setSortingEnabled(True)

        self.table_sales.setCurrentCell(self.row,0)
        self.show_detail()

    def show_detail(self):
        print 'ccccccccccccccccccccccccccccccc'
        date_str = str(self.parent().parent().date.toString('yyyyMMdd'))
        json_data=open('db/history/' + date_str + '.json').read()
        self.history_data = json.loads(json_data)
        
        self.row = self.table_sales.currentRow()
        detail = str(self.table_sales.item(self.row, 0).text())

        self.table_detail.setSortingEnabled(False)
        r = self.table_detail.rowCount()
        while r > 0:
            self.table_detail.removeRow(r-1)
            r = self.table_detail.rowCount()

        for key, value in self.history_data[detail][u'Items'].iteritems():
            r = self.table_detail.rowCount()
            self.table_detail.insertRow(r)

            barcode = str(key)
            price = "{:.2f}".format(self.history_data[detail][u'Price'][key])
            units = str(value)
            total = "{:.2f}".format(self.history_data[detail][u'Price'][key]*value)
            for items in items_list:
                if items['Barcode'] == barcode:
                    name = items['Item Name']

            self.table_detail.setItem(r , 0, QtGui.QTableWidgetItem(barcode))
            self.table_detail.setItem(r , 1, QtGui.QTableWidgetItem(name))
            self.table_detail.setItem(r , 2, QtGui.QTableWidgetItem(price))
            self.table_detail.item(r, 2).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            self.table_detail.setItem(r , 3, QtGui.QTableWidgetItem(units))
            self.table_detail.item(r, 3).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            self.table_detail.setItem(r , 4, QtGui.QTableWidgetItem(total))
            self.table_detail.item(r, 4).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.table_detail.setSortingEnabled(True)
        self.table_detail.sortItems(1)

    def add_detail(self):
        self.edit_app = EditDetail_window(self, action='add')
        self.edit_app.show()
        self.edit_app.activateWindow()

    def remove_detail(self):
        global date_data, history_data

        items_list = []
        with open('db/ItemList.csv','r') as f:
            # print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                # print items
                items_list.append(items)


        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
        history_data = json.loads(json_data)





        date_str = self.table_sales.item(self.selectedRow_sales,0).text()
        barcode = self.table_detail.item(self.selectedRow_detail,0).text()

        print 'total price*****************'
        print history_data[unicode(str(date_str))][u'Total Price']
        
        history_data[unicode(str(date_str))][u'Total Price'] -= float(self.table_detail.item(self.selectedRow_detail,4).text())
        
        date_s = str(date_str)[:8]
        date_data[unicode(date_s)][u'Daily Sales'] -= float(self.table_detail.item(self.selectedRow_detail,4).text())
        date_data['Drawer']['Money'] -= float(self.table_detail.item(self.selectedRow_detail,4).text())
        date_data[unicode(date_s)][u'Item Sales'][unicode(str(barcode))] -= int(str(self.table_detail.item(self.selectedRow_detail,3).text()))
        date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))] += int(str(self.table_detail.item(self.selectedRow_detail,3).text()))
        del history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))]
        del history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))]


        file = open('db/ItemList.csv','w')
        fcsv = csv.writer(file, lineterminator='\n')
        for items in items_list:
            if items['Barcode'] == str(barcode):
                items['Stock'] = str(date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))])
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            fcsv.writerow(info)
        file.close()

        UpdateJSON('none', [])

        self.RefreshTable()
        
        
    def edit_detail(self):
        self.edit_app = EditDetail_window(self, action='edit')
        self.edit_app.show()
        self.edit_app.activateWindow()

    def updateSelected_sales(self):
        self.selectedRow_sales = self.table_sales.currentRow()
    def updateSelected_detail(self):
        self.selectedRow_detail = self.table_detail.currentRow()

class EditDetail_window(QtGui.QDialog, Ui_EditDetailWindow):
    def __init__(self, parent=None, action='add'):
        print 'eeeeeeeeeeeeeeeeeeeeeeeeeee'


        items_list = []
        with open('db/ItemList.csv','r') as f:
            # print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                # print items
                items_list.append(items)




        for items in items_list:
                             
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            print info


        # date_str = str(self.parent().parent().date.toString('yyyyMMdd'))
        # json_data=open('db/history/' + date_str + '.json').read()
        # self.history_data = json.loads(json_data)


        super(EditDetail_window, self).__init__(parent)
        self.setupUi(self)

        self.action = action

        self.onlydouble = QDoubleValidator()
        self.onlyint = QIntValidator()
        self.line_price.setValidator(self.onlydouble)
        self.line_units.setValidator(self.onlyint)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateInfo)
        self.timer.start(500)
        self.row = -1

        self.edit_button.clicked.connect(self.EditDetail)
        self.line_barcode.textChanged.connect(self.BarcodeChange)

        self.line_barcode.setFocus(True)

        if action == 'add':
            self.edit_button.setText(u'เพิ่ม')
        else:
            self.edit_button.setText(u'แก้ไข')

    def BarcodeChange(self):
        for items in items_list:
            if self.line_barcode.text() == items['Barcode']:
                self.line_name.setText(items['Item Name'])
                self.line_price.setText(items['Price'])

    def EditDetail(self):
        print 'edit detailllllllllllll'


        items_list = []
        with open('db/ItemList.csv','r') as f:
            # print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                # print items
                items_list.append(items)




        for items in items_list:
                             
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            print info

            
        




        for items in items_list:
                             
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            print info





        global date_data, history_data
        # -----------------------------------------------
        date_data = {}
        history_data = {}

        with open('db/data.json') as f:
            date_data = json.load(f)
        # print date_data

        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        print curr_date_str

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
            history_data = json.loads(json_data)

        # ----------------------------------------------------

        
        
        

        print '-----------------------------------------------------------------------------'
        print ''
        print ''
        print 'SELECTED!!!'
        print 'date : '
        date_str = self.parent().table_sales.item(self.parent().selectedRow_sales,0).text()
        print date_str

        print 'date only day : '
        date_s = str(date_str)[:8]
        print date_s

        print 'barcode : '
        barcode = self.line_barcode.text()
        print barcode

        print 'price/unit : '      
        price = float(str(self.line_price.text()))
        print price

        # print 'old unit: '
        # old_unit = int(str(self.parent().table_detail.item(self.parent().selectedRow_detail,3).text()))
        # print old_unit

        print 'new unit : '
        new_unit = int(str(self.line_units.text()))
        print new_unit

        # print 'delta_unit : '  
        # delta_unit = int(str(self.line_units.text()))-int(str(self.parent().table_detail.item(self.parent().selectedRow_detail,3).text()))
        # print delta_unit
         


        

        # if self.action == 'add':
        #     print 'add new kind***************'
        #     if unicode(str(barcode)) in history_data[unicode(str(date_str))][u'Items']:
        #         current_num_items = history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))]
        #     history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))] = float(str(self.line_price.text()))
        # else:
        #     print 'edit detail****************'





        print ''
        print ''
        print '-----------------------------------------------------------------------------'






        current_num_items = 0
        if self.action == 'add':
            if unicode(str(barcode)) in history_data[unicode(str(date_str))][u'Items']:
                current_num_items = history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))]
            history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))] = float(str(self.line_price.text()))
        else:
            date_data[unicode(date_s)][u'Daily Sales'] -= float(self.parent().table_detail.item(self.parent().selectedRow_detail,4).text())
            date_data['Drawer']['Money'] -= float(self.parent().table_detail.item(self.parent().selectedRow_detail,4).text())
            history_data[unicode(str(date_str))][u'Total Price'] -= float(self.parent().table_detail.item(self.parent().selectedRow_detail,4).text())
            date_data[unicode(date_s)][u'Item Sales'][unicode(str(barcode))] -= int(str(self.parent().table_detail.item(self.parent().selectedRow_detail,3).text()))
            
            print '3333333333333333333333333333333333333333333'
            print date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))]

            date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))] += int(str(self.parent().table_detail.item(self.parent().selectedRow_detail,3).text()))

            print date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))]


        history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))] = current_num_items + int(str(self.line_units.text()))
        history_data[unicode(str(date_str))][u'Total Price'] += int(str(self.line_units.text())) * history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))]
        date_data[unicode(date_s)][u'Daily Sales'] += int(str(self.line_units.text())) * history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))]
        date_data['Drawer']['Money'] += int(str(self.line_units.text())) * history_data[unicode(str(date_str))][u'Price'][unicode(str(barcode))]
        # date_data[unicode(date_s)][u'Item Sales'][unicode(str(barcode))] += int(str(self.line_units.text()))

        print 'item saaaaaaaaaaaa-------'
        # print 
        # print history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))]
        # print date_data[unicode(date_s)][u'Item Sales'][unicode(str(barcode))]

        if date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))]:

            date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))] -= history_data[unicode(str(date_str))][u'Items'][unicode(str(barcode))]
        else:
            'print unknown'
        print 'xxxxxxxxxxxx'
        
        file = open('db/ItemList.csv','w')
        fcsv = csv.writer(file, lineterminator='\n')
        for items in items_list:
            if items['Barcode'] == str(barcode):
                print 'barcode ---------------------------'
                print str(barcode)
                print 'unit ---------------------------'
                print str(date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))])
                items['Stock'] = str(date_data[unicode(date_s)][u'Current Stock'][unicode(str(barcode))])

                 
            info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
            print info
            fcsv.writerow(info)
        file.close()

        # items_list = []
        # with open('db/ItemList.csv','r') as f:
        #     print f
        #     for line in f:
        #         print line
        #         line_split = line.strip().split(',')
        #         (barcode,name,price,stock) = line_split
        #         items = items_info.copy()
        #         items['Barcode'] = barcode
        #         items['Item Name'] = unicode(name, "utf-8")
        #         items['Price'] = price
        #         items['Stock'] = stock
        #         # print items
        #         items_list.append(items)


        








        UpdateJSON('none', [])
        
        self.parent().RefreshTable()
        self.close()

    def updateInfo(self):

        # for items in items_list:
                             
        #     info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
        #     print info



        if self.action == 'edit':
            if self.parent().selectedRow_detail > -1:
                self.row = self.parent().selectedRow_detail
                self.line_barcode.setText(self.parent().table_detail.item(self.row, 0).text())
                self.line_name.setText(self.parent().table_detail.item(self.row, 1).text())
                self.line_price.setText(self.parent().table_detail.item(self.row, 2).text())
                # self.line_units.setText(self.parent().table_detail.item(self.row, 3).text())

class ShortcutEditor_window(QtGui.QDialog, Ui_ShortcutWindow):
    def __init__(self, parent=None, action='add'):
        super(ShortcutEditor_window, self).__init__(parent)
        self.setupUi(self)

        self.action = action

        self.selectedRow = -1
        self.table_stock.clicked.connect(self.updateSelected)
        self.done_button.clicked.connect(self.editShortcut)

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_stock.setHorizontalHeaderLabels(header)
        header = self.table_stock.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)

        # ----------------------------
        items_list = []
        with open('db/ItemList.csv','r') as f:
            print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                
                items_list.append(items)


        # with open('db/data.json') as f:
        #     date_data = json.load(f)


        # curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        # print curr_date_str

        # if os.path.exists('db/history/' + curr_date_str + '.json'):
        #     json_data=open('db/history/' + curr_date_str + '.json').read()
        #     history_data = json.loads(json_data)

        # ---------------------------------------

        for items in items_list:
            item_array = [items['Barcode'], items['Item Name'], items['Price'], items['Stock']]
            r = self.table_stock.rowCount()
            self.table_stock.insertRow(r)
            for i in range(len(item_array)):
                self.table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                if i > 1:
                    self.table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.table_stock.sortItems(1)

    def updateSelected(self):
        self.selectedRow = self.table_stock.currentRow()

    def editShortcut(self):
        row = self.parent().shortcut_row
        col = self.parent().shortcut_col
        if self.action == 'add':
            if self.parent().table_shortcut.cellWidget(row,col) is None:
                A = QLabel(self.table_stock.item(self.selectedRow, 1).text() + '\n' + self.table_stock.item(self.selectedRow, 0).text() + '\n' + self.table_stock.item(self.selectedRow, 2).text() + u' บาท', self)
                A.setGeometry(QtCore.QRect(0, 0, 300, 100)) 
                A.setAlignment(Qt.AlignCenter)
                if (row+col)%2 == 0:
                    A.setStyleSheet("background-color: rgba(135, 255, 157, 150)")
                else:
                    A.setStyleSheet("background-color: rgba(255, 167, 135, 150)")
                self.parent().table_shortcut.setCellWidget(row, col, A)
                self.parent().table_shortcut.resizeRowsToContents()
                self.parent().table_shortcut.resizeColumnsToContents()
        else:
            self.parent().table_shortcut.removeCellWidget(row,col)
        self.parent().save_shortcut_button()
        self.close()

class Finish_window(QtGui.QDialog, Ui_FinishWindow):
    def __init__(self, parent=None):
        super(Finish_window, self).__init__(parent)
        self.setupUi(self)

        self.onlydouble = QDoubleValidator()
        self.line_received.setValidator(self.onlydouble)
        self.line_change.setValidator(self.onlydouble)

        self.line_received.textChanged.connect(self.ReceivedChange)
        self.done_button.clicked.connect(self.Done)
        self.cancel_button.clicked.connect(self.Cancel)

        self.line_received.setFocus(True)

        self.line_change.setStyleSheet("background-color: rgb(255, 255, 0);color: rgb(255,0,0)")

    def ReceivedChange(self):
        if self.line_received.text() != '':
            change = float(self.line_received.text()) - float(self.line_total.text())
            change = "{:.2f}".format(change)
            self.line_change.setText(change)
        else:
            self.line_change.setText("{:.2f}".format(-float(self.line_total.text())))
        self.line_change.setAlignment(QtCore.Qt.AlignRight)

    def keyPressEvent(self, qKeyEvent):
        if ( qKeyEvent.key() == QtCore.Qt.Key_Return ) or ( qKeyEvent.key() == QtCore.Qt.Key_Enter ): 
            self.Done()

    def Done(self):
        print 'doneeeeeeeeeeeeeeeeeeeeeeeeeeeeee'

        # ----------------------------
        date_data = {}
        history_data = {}
        items_list = []
        with open('db/ItemList.csv','r') as f:
            print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                
                items_list.append(items)


        with open('db/data.json') as f:
            date_data = json.load(f)


        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        print curr_date_str

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
            history_data = json.loads(json_data)

        # ---------------------------------------

        # global items_list, history_data
        
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        date_time_str = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")

        if float(self.line_change.text()) >= 0:
            self.parent().selectedRow = -1
            r = self.parent().table.rowCount()

            out_of_stock = False
            for row in range(r):
                for ii in range(len(items_list)):
                    item = items_list[ii]
                    if self.parent().table.item(row, 0).text() == item['Barcode']:
                        if int(item['Stock']) - int(self.parent().table.item(row, 3).text()) >= 0:
                            if date_time_str in history_data:
                                pass
                            else:
                                history_data[date_time_str] = {
                                                                'Total Price': 0,
                                                                'Price': {},
                                                                'Items': {}
                                                            }
                            
                            item['Stock'] = str(int(item['Stock']) - int(self.parent().table.item(row, 3).text()))
                            print 'jjjjjjjjjjjjjjjjjjjjjjjjjjjjj'
                            UpdateJSON('sell', [item['Barcode'], int(self.parent().table.item(row, 3).text()), float(self.parent().table.item(row, 4).text())])
                            history_data[unicode(date_time_str)][u'Items'][item['Barcode']] = int(str(self.parent().table.item(row, 3).text()))
                            history_data[unicode(date_time_str)][u'Price'][item['Barcode']] = float(str(self.parent().table.item(row, 2).text()))
                            history_data[unicode(date_time_str)][u'Total Price'] += float(self.parent().table.item(row, 4).text())
                            break
                        else:
                            out_of_stock = True
                            break

            if out_of_stock:
                self.showErrorDialog2()
            else:
                with open('db/history/'+date_str + '.json', 'w') as fp:
                    json.dump(history_data, fp, sort_keys=True, indent=4, separators=(',', ': '))

                file = open('db/ItemList.csv','w')
                print 'd11111111111111111111111111111111111111111'
                fcsv = csv.writer(file, lineterminator='\n')
                for items in items_list:
                    info = [items['Barcode'], items['Item Name'].encode('utf-8'), items['Price'], items['Stock']]
                    fcsv.writerow(info)
                file.close()

                UpdateJSON('',0)

                self.showSuccessDialog()
                self.parent().ClearList()
                # time.sleep(1)
                self.parent().selectedRow = -1
                self.close()
        else:
            self.showErrorDialog()

    def showErrorDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)

        txtmsg = "ได้รับเงินไม่ครบ ต้องการอีก " + '{:.2f}'.format(-float(self.line_change.text())) + ' บาท'
        txtmsg = unicode(txtmsg, 'utf-8')
        msg.setText(txtmsg)
        msg.setWindowTitle(u"Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def showErrorDialog2(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)

        txtmsg = "สินค้าในคลังไม่เพียงพอ"
        txtmsg = unicode(txtmsg, 'utf-8')
        msg.setText(txtmsg)
        msg.setWindowTitle(u"Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def showSuccessDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)

        txtmsg = "ยอดสินค้า " + self.line_total.text() + ' บาท\nได้รับเงิน ' + '{:.2f}'.format(float(self.line_received.text())) + ' บาท\nทอนเงิน ' + self.line_change.text() + ' บาท'
        txtmsg = unicode(txtmsg, 'utf-8')
        msg.setText(txtmsg)
        msg.setWindowTitle(u"Done")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    def Cancel(self):
        self.close()

class EditUnitsTable_window(QtGui.QDialog, Ui_EditUnitsTableWindow):
    def __init__(self, parent=None):
        super(EditUnitsTable_window, self).__init__(parent)
        self.setupUi(self)
        self.edit_button.clicked.connect(self.editUnits)

        self.onlyint = QIntValidator()
        self.line_units.setValidator(self.onlyint)
        self.line_units.setFocus(True)
        self.line_units.selectAll()
        self.line_units.setText(self.parent().table.item(self.parent().current_edit_row,3).text())

    def editUnits(self):
        self.parent().table.setItem(self.parent().current_edit_row,3, QtGui.QTableWidgetItem(self.line_units.text()))
        total = float(self.parent().table.item(self.parent().current_edit_row,2).text()) * int(self.parent().table.item(self.parent().current_edit_row,3).text())
        self.parent().table.setItem(self.parent().current_edit_row,4, QtGui.QTableWidgetItem("{:.2f}".format(total)))
        self.parent().table.item(self.parent().current_edit_row,3).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.parent().table.item(self.parent().current_edit_row,4).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

        total_price = 0.0
        r = self.parent().table.rowCount()
        for row in range(r):
            total_price += float(self.parent().table.item(row, 4).text())
        self.parent().total_price.setText("{:.2f}".format(total_price))
        self.parent().total_price.setAlignment(QtCore.Qt.AlignRight)
        self.close()

class DepWit_window(QtGui.QDialog, Ui_DepWitWindow):
    def __init__(self, parent=None, action='deposit'):
        super(DepWit_window, self).__init__(parent)
        self.setupUi(self)

        self.action = action
        self.onlydouble = QDoubleValidator()
        self.line_money.setValidator(self.onlydouble)

        if self.action == 'deposit':
            self.setWindowTitle(u'ฝากเงิน')
            self.money_label.setText(u'ฝากเงินเข้าลิ้นชัก')
            self.money_button.setText(u'ฝากเงิน')
        else:
            self.setWindowTitle(u'ถอนเงิน')
            self.money_label.setText(u'ถอนเงินจากลิ้นชัก')
            self.money_button.setText(u'ถอนเงิน')

        self.money_button.clicked.connect(self.buttonClicked)

    def buttonClicked(self):
        global date_data
        date_time_str = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
        if self.action == 'deposit':
            date_data['Drawer']['Money'] += float(self.line_money.text())
            date_data['Drawer'][date_time_str] = {}
            date_data['Drawer'][date_time_str]['Activity'] = 'Deposit'
            date_data['Drawer'][date_time_str]['Money'] = float(self.line_money.text())
        else:
            date_data['Drawer']['Money'] -= float(self.line_money.text())
            date_data['Drawer'][date_time_str] = {}
            date_data['Drawer'][date_time_str]['Activity'] = 'Withdraw'
            date_data['Drawer'][date_time_str]['Money'] = float(self.line_money.text())

        UpdateJSON('none', [])
        self.close()

class DrawerHistory_window(QtGui.QDialog, Ui_DrawerHistoryWindow):
    def __init__(self, parent=None):

        # ----------------------------
        items_list = []
        with open('db/ItemList.csv','r') as f:
            print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                
                items_list.append(items)


        with open('db/data.json') as f:
            date_data = json.load(f)


        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        print curr_date_str

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
            history_data = json.loads(json_data)

        # ---------------------------------------

        super(DrawerHistory_window, self).__init__(parent)
        self.setupUi(self)

        header = ['วันที่-เวลา', 'ฝาก/ถอน', 'จำนวนเงิน']
        header = [ unicode(h, "utf-8") for h in header]
        self.table_history.setHorizontalHeaderLabels(header)
        header = self.table_history.horizontalHeader()
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(2, QtGui.QHeaderView.Stretch)
        for key, value in date_data['Drawer'].iteritems():
            if key == 'Money':
                continue

            r = self.table_history.rowCount()
            self.table_history.insertRow(r)
            self.table_history.setItem(r , 0, QtGui.QTableWidgetItem(str(key)))
            self.table_history.setItem(r , 2, QtGui.QTableWidgetItem("{:.2f}".format(value['Money'])))
            self.table_history.item(r, 2).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        
            if str(value['Activity']) == 'Deposit':
                self.table_history.setItem(r , 1, QtGui.QTableWidgetItem(u'ฝากเงิน'))
                self.table_history.item(r, 1).setTextAlignment(QtCore.Qt.AlignCenter)
                for i in range(3):
                    self.table_history.item(r, i).setBackground(QtGui.QColor(173, 255, 0))
            else:
                self.table_history.setItem(r , 1, QtGui.QTableWidgetItem(u'ถอนเงิน'))
                self.table_history.item(r, 1).setTextAlignment(QtCore.Qt.AlignCenter)
                for i in range(3):
                    self.table_history.item(r, i).setBackground(QtGui.QColor(255, 173, 0))
        self.table_history.sortItems(0, Qt.DescendingOrder)

class MyApp(QtGui.QMainWindow, Ui_MainWindow):
    print 'MyApp...................'
    def __init__(self):
        print 'MyApp init'
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.setMouseTracking(True)

        self.BP = Barcode_process()

        self.add_shortcut_button.setStyleSheet("background-color: rgb(178, 255, 178)")
        self.remove_shortcut_button.setStyleSheet("background-color: rgb(255, 178, 178)")
        self.num_shortcut_button = 0
        self.shortcut_button = []
        self.shortcut_row = 0
        self.shortcut_col = 0
        self.button_per_row = 3
        self.button_per_col = 8
        self.table_shortcut.cellClicked.connect(self.shortcut_click)
        self.table_shortcut.cellDoubleClicked.connect(self.shortcut_doubleclick)
        self.load_shortcut_button()

        self.add_app = Add_window(self)
        self.stock_app = Stock_window(self)
        self.finish_app = Finish_window(self)
        self.date_app = DateInfo_window(self)
       
        self.add_button.clicked.connect(self.OpenAddWindow)
        self.remove_button.clicked.connect(self.RemoveSelectedRow)
        self.clear_button.clicked.connect(self.ClearList)
        self.stock_button.clicked.connect(self.OpenStockWindow)
        self.finish_button.clicked.connect(self.FinishState)
        self.calendar.clicked[QtCore.QDate].connect(self.CalendarClicked)
        self.add_shortcut_button.clicked.connect(self.OpenAddShortcut)
        self.remove_shortcut_button.clicked.connect(self.OpenRemoveShortcut)
        self.date = 0

        dd = QDate.currentDate()
        ff = QTextCharFormat()
        ff.setFontUnderline(True)
        ff.setFontWeight(75)
        self.calendar.setDateTextFormat(dd, ff)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateWidget)
        self.timer.start(300) 

        self.selectedRow = -1
        self.table.clicked.connect(self.updateSelected)

        self.total_price.setText("{:.2f}".format(0.00))
        self.total_price.setAlignment(QtCore.Qt.AlignRight)

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน', 'ราคารวม']
        header = [ unicode(h, "utf-8") for h in header]
        self.table.setHorizontalHeaderLabels(header)
        header = self.table.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(4, QtGui.QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.editUnits)

        self.UpdateTotalLabel()
        self.deposit_button.clicked.connect(self.DepositDrawer)
        self.withdraw_button.clicked.connect(self.WithdrawDrawer)
        self.drawer_history_button.clicked.connect(self.DrawerHistory)

    def DepositDrawer(self):
        print 'MyApp.DepositDrawer'
        self.depwit_app = DepWit_window(self, action='deposit')
        self.depwit_app.show()
        self.depwit_app.activateWindow()

    def WithdrawDrawer(self):
        print 'MyApp.WithdrawDrawer'
        self.depwit_app = DepWit_window(self, action='withdraw')
        self.depwit_app.show()
        self.depwit_app.activateWindow()

    def DrawerHistory(self):
        print 'MyApp. DrawerHistory'
        self.drawerhistory_app = DrawerHistory_window(self)
        self.drawerhistory_app.show()
        self.drawerhistory_app.activateWindow()

    def UpdateTotalLabel(self):
        # print 'MyApp.  UpdateTotalLabel8888888888888888888888'
        # -----------------------------------------------------
        with open('db/data.json') as f:
            date_data = json.load(f)
        # ------------------------------------------------
        monthly = 0.0
        daily = 0.0
        month_str = datetime.datetime.now().strftime("%Y%m")
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        
        for k, v in date_data.iteritems():
            if str(k[:6]) == month_str:
                monthly += v[u"Daily Sales"]

            if str(k) == date_str:
                daily = v[u"Daily Sales"]

        daily_str = 'ยอดขายประจำวัน ' + '{:.2f}'.format(daily) + ' บาท'
        daily_str = unicode(daily_str, 'utf:-8')
        self.daily_label.setText(daily_str)

        monthly_str = 'ยอดขายประจำเดือน ' + '{:.2f}'.format(monthly) + ' บาท'
        monthly_str = unicode(monthly_str, 'utf:-8')
        self.monthly_label.setText(monthly_str)

        drawer_str = 'จำนวนเงินในลิ้นชัก ' + '{:.2f}'.format(date_data['Drawer']['Money']) + ' บาท'
        drawer_str = unicode(drawer_str, 'utf:-8')
        self.drawer_label.setText(drawer_str)

    def editUnits(self, row, column):
        
        self.current_edit_row = row
        self.edit_units_app = EditUnitsTable_window(self)
        self.edit_units_app.show()
        self.edit_units_app.activateWindow()

    def save_shortcut_button(self):
        file_sb = open('db/sb.csv','w')
        for row in range(self.button_per_col):
            for col in range(self.button_per_row):
                if self.table_shortcut.cellWidget(row,col) is not None:
                    barcode = str(self.table_shortcut.cellWidget(row,col).text().split('\n')[1])
                    file_sb.write(barcode + ',' + str(row) + ',' + str(col) + '\n')
        file_sb.close()

    def refresh_shortcut_button(self):
        for row in range(self.button_per_col):
            for col in range(self.button_per_row):
                self.table_shortcut.removeCellWidget(row,col)

        r = self.table_shortcut.rowCount()
        while r > 0:
            self.table_shortcut.removeRow(r-1)
            r = self.table_shortcut.rowCount()
        self.load_shortcut_button()

    def load_shortcut_button(self):
        header = self.table_shortcut.horizontalHeader()
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(2, QtGui.QHeaderView.Stretch)
        for i in range(self.button_per_col):
            row = self.table_shortcut.rowCount()
            self.table_shortcut.insertRow(row)

        with open('db/sb.csv','r') as f:
            for line in f:
                barcode = line.strip().split('\n')[0].strip().split(',')[0]
                row = int(line.strip().split('\n')[0].strip().split(',')[1])
                col = int(line.strip().split('\n')[0].strip().split(',')[2])
                for items in items_list:
                    if barcode == items['Barcode']:
                        A = QLabel(items['Item Name'] + '\n' + items['Barcode'] + '\n' + items['Price'] + u' บาท', self)
                        A.setGeometry(QtCore.QRect(0, 0, 300, 100)) 
                        A.setAlignment(Qt.AlignCenter)
                        if (row+col)%2 == 0:
                            A.setStyleSheet("background-color: rgba(135, 255, 157, 150)")
                        else:
                            A.setStyleSheet("background-color: rgba(255, 167, 135, 150)")
                        self.table_shortcut.setCellWidget(row, col, A)
                        self.table_shortcut.resizeRowsToContents()
                        self.table_shortcut.resizeColumnsToContents()

    def shortcut_doubleclick(self, row, column):
        if self.table_shortcut.cellWidget(row,column) is None:
            self.shortcut_row = row
            self.shortcut_col = column
        else:
            barcode = str(self.table_shortcut.cellWidget(row,column).text().split('\n')[1])

            acquired_item = items_info.copy()
            isInList = False
            for items in items_list:
                if barcode == items['Barcode']:
                    acquired_item['Barcode'] = items['Barcode']
                    acquired_item['Item Name'] = items['Item Name']
                    acquired_item['Price'] = "{:.2f}".format(float(items['Price']))
                    acquired_item['Unit'] = '1'
                    acquired_item['Total'] = "{:.2f}".format( int(acquired_item['Unit'])*float(acquired_item['Price']) )
                    isInList = True

            if isInList:
                r = self.table.rowCount()
                isDuplicate = -1
                for row in range(r):
                    if self.table.item(row, 0).text() == acquired_item['Barcode']:
                        isDuplicate = row
                        num_unit = int(acquired_item['Unit']) + int(self.table.item(row, 3).text())
                        acquired_item['Unit'] = str(num_unit)
                        acquired_item['Total'] = "{:.2f}".format( int(acquired_item['Unit'])*float(acquired_item['Price']) )

                item_array = [acquired_item['Barcode'], acquired_item['Item Name'], acquired_item['Price'], acquired_item['Unit'], acquired_item['Total']]
                if isDuplicate == -1:
                    self.table.insertRow(r)
                    for i in range(len(item_array)):
                        self.table.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.table.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                else:
                    row = isDuplicate
                    for i in range(len(item_array)):
                        self.table.setItem(row , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.table.item(row, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                r = self.table.rowCount()
                total_price = 0.0
                for row in range(r):
                    total_price += float(self.table.item(row, 4).text())
                self.total_price.setText("{:.2f}".format(total_price))
                self.total_price.setAlignment(QtCore.Qt.AlignRight)
                self.table_shortcut.clearSelection()   
        
    def shortcut_click(self, row, column):
        self.shortcut_row = row
        self.shortcut_col = column

    def OpenAddShortcut(self):
        self.shortcut_app = ShortcutEditor_window(self, action='add')
        self.shortcut_app.show()
        self.shortcut_app.activateWindow()

    def OpenRemoveShortcut(self):
        row = self.shortcut_row
        col = self.shortcut_col
        self.table_shortcut.removeCellWidget(row,col)
        self.save_shortcut_button()
        self.table_shortcut.clearSelection() 

    def ShowCalendarInfo(self, date):

        # ----------------------------
        items_list = []
        with open('db/ItemList.csv','r') as f:
            print f
            for line in f:
                print line
                line_split = line.strip().split(',')
                (barcode,name,price,stock) = line_split
                items = items_info.copy()
                items['Barcode'] = barcode
                items['Item Name'] = unicode(name, "utf-8")
                items['Price'] = price
                items['Stock'] = stock
                
                items_list.append(items)


        with open('db/data.json') as f:
            date_data = json.load(f)


        curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
        print curr_date_str

        if os.path.exists('db/history/' + curr_date_str + '.json'):
            json_data=open('db/history/' + curr_date_str + '.json').read()
            history_data = json.loads(json_data)

        # ---------------------------------------

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.date_app.table_sales.setHorizontalHeaderLabels(header)
        header = self.date_app.table_sales.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.date_app.table_add.setHorizontalHeaderLabels(header)
        header = self.date_app.table_add.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)

        header = ['รหัสสินค้า', 'ชื่อสินค้า', 'ราคาต่อหน่วย', 'จำนวน']
        header = [ unicode(h, "utf-8") for h in header]
        self.date_app.table_stock.setHorizontalHeaderLabels(header)
        header = self.date_app.table_stock.horizontalHeader()
        header.setResizeMode(1, QtGui.QHeaderView.Stretch)
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)

        self.date = date

        r = self.date_app.table_sales.rowCount()
        while r > 0:
            self.date_app.table_sales.removeRow(r-1)
            r = self.date_app.table_sales.rowCount()

        r = self.date_app.table_add.rowCount()
        while r > 0:
            self.date_app.table_add.removeRow(r-1)
            r = self.date_app.table_add.rowCount()

        r = self.date_app.table_stock.rowCount()
        while r > 0:
            self.date_app.table_stock.removeRow(r-1)
            r = self.date_app.table_stock.rowCount()

        date_str = str(date.toString('yyyy-MM-dd'))
        data_str = 'สรุปรายการประจำวันที่ ' + date_str
        data_str = unicode(data_str, 'utf-8')
        self.date_app.label_date.setText(data_str)

        date_str = str(date.toString('yyyyMMdd'))
        if date_str in date_data:
            data_str = 'ยอดขายรวม ' + "{:.2f}".format(date_data[date_str]['Daily Sales']) + ' บาท'
            data_str = unicode(data_str, 'utf-8')
            self.date_app.label_sales.setText(data_str)

            for key, value in date_data[date_str]['Item Sales'].iteritems():
                if value > 0:
                    for items in items_list:
                        if key == items['Barcode']:
                            item_array = [items['Barcode'], items['Item Name'], items['Price'], str(value)]
                            r = self.date_app.table_sales.rowCount()
                            self.date_app.table_sales.insertRow(r)
                            for i in range(len(item_array)):
                                self.date_app.table_sales.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                                if i > 1:
                                    self.date_app.table_sales.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                                for kk, vv in date_data[date_str]['Changed Price'].iteritems():
                                    if vv['Barcode'] == items['Barcode']:
                                        self.date_app.table_sales.item(r, i).setBackground(QtGui.QColor(255,255,0))
                            break

            z = {}
            for kk, vv in date_data[date_str]['Stock Adding'].iteritems():
                z = merge(z, vv, lambda x,y: x+y)

            for key, value in z.iteritems():
                if value > 0:
                    for items in items_list:
                        if key == items['Barcode']:
                            item_array = [items['Barcode'], items['Item Name'], items['Price'], str(value)]
                            r = self.date_app.table_add.rowCount()
                            self.date_app.table_add.insertRow(r)
                            for i in range(len(item_array)):
                                self.date_app.table_add.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                                if i > 1:
                                    self.date_app.table_add.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                            break

            for key, value in date_data[date_str]['Current Stock'].iteritems():
                for items in items_list:
                    if key == items['Barcode']:
                        if int(items['Stock']) > -1:
                            item_array = [items['Barcode'], items['Item Name'], items['Price'], str(value)]
                            r = self.date_app.table_stock.rowCount()
                            self.date_app.table_stock.insertRow(r)
                            for i in range(len(item_array)):
                                self.date_app.table_stock.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                                if i > 1:
                                    self.date_app.table_stock.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                            break

            self.date_app.table_sales.sortItems(1)
            self.date_app.table_add.sortItems(1)
            self.date_app.table_stock.sortItems(1)
        else:
            data_str = 'ไม่พบข้อมูล'
            data_str = unicode(data_str, 'utf-8')
            self.date_app.label_sales.setText(data_str)
        
    def CalendarClicked(self,date):
        del self.date_app
        self.date_app = DateInfo_window(self)
        self.ShowCalendarInfo(date)
        self.date_app.show()
        self.date_app.activateWindow()

    def keyPressEvent(self, qKeyEvent):
        # if ( qKeyEvent.key() == QtCore.Qt.Key_Return ) or ( qKeyEvent.key() == QtCore.Qt.Key_Enter ): 
        #     self.FinishState()
        if( qKeyEvent.key() == QtCore.Qt.Key_Enter): 
            self.FinishState()

    def FinishState(self):
        self.finish_app.line_total.setText(self.total_price.toPlainText())
        self.finish_app.line_total.setAlignment(QtCore.Qt.AlignRight)
        self.finish_app.line_received.setText('')
        self.finish_app.line_received.setAlignment(QtCore.Qt.AlignRight)
        self.finish_app.line_change.setText("{:.2f}".format(-float(self.total_price.toPlainText())))
        self.finish_app.line_change.setAlignment(QtCore.Qt.AlignRight)
        self.finish_app.line_received.setFocus(True)
        self.finish_app.show()
        self.finish_app.activateWindow()

    def ClearList(self):
        self.total_price.setText("{:.2f}".format(0.00))
        self.total_price.setAlignment(QtCore.Qt.AlignRight)

        r = self.table.rowCount()
        while r > 0:
            self.table.removeRow(r-1)
            r = self.table.rowCount()

    def OpenAddWindow(self):
        del self.add_app
        self.add_app = Add_window(self)
        self.add_app.line_barcode.setText('')
        self.add_app.line_name.setText('')
        self.add_app.line_price.setText('')
        self.add_app.line_units.setText('')
        self.add_app.show()
        self.add_app.activateWindow()

    def OpenStockWindow(self):
        del self.stock_app
        self.stock_app = Stock_window(self)
        self.stock_app.show()
        self.stock_app.activateWindow()
        x=1

    def updateSelected(self):
        self.selectedRow = self.table.currentRow()

    def RemoveSelectedRow(self):
        if self.selectedRow > -1:
            self.total_price.setText("{:.2f}".format(float(self.total_price.toPlainText()) - float(self.table.item(self.selectedRow, 4).text())))
            self.total_price.setAlignment(QtCore.Qt.AlignRight)

            self.table.removeRow(self.selectedRow)
            self.table.clearSelection()
            self.selectedRow = -1

    def updateWidget(self):
        # print 'MyApp .updateWidget9999999999999999999999999'

        self.UpdateTotalLabel()
        if not self.isActiveWindow():
            self.BP.barcode = []

        for l in self.BP.barcode:
            acquired_item = items_info.copy()
            isInList = False
            for items in items_list:
                if l == items['Barcode']:
                    acquired_item['Barcode'] = items['Barcode']
                    acquired_item['Item Name'] = items['Item Name']
                    acquired_item['Price'] = "{:.2f}".format(float(items['Price']))
                    acquired_item['Unit'] = '1'
                    acquired_item['Total'] = "{:.2f}".format( int(acquired_item['Unit'])*float(acquired_item['Price']) )
                    isInList = True

            if isInList:
                r = self.table.rowCount()
                isDuplicate = -1
                for row in range(r):
                    if self.table.item(row, 0).text() == acquired_item['Barcode']:
                        isDuplicate = row
                        num_unit = int(acquired_item['Unit']) + int(self.table.item(row, 3).text())
                        acquired_item['Unit'] = str(num_unit)
                        acquired_item['Total'] = "{:.2f}".format( int(acquired_item['Unit'])*float(acquired_item['Price']) )

                item_array = [acquired_item['Barcode'], acquired_item['Item Name'], acquired_item['Price'], acquired_item['Unit'], acquired_item['Total']]
                if isDuplicate == -1:
                    self.table.insertRow(r)
                    for i in range(len(item_array)):
                        self.table.setItem(r , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.table.item(r, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                else:
                    row = isDuplicate
                    for i in range(len(item_array)):
                        self.table.setItem(row , i, QtGui.QTableWidgetItem(item_array[i]))
                        if i > 1:
                            self.table.item(row, i).setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                r = self.table.rowCount()
                total_price = 0.0
                for row in range(r):
                    total_price += float(self.table.item(row, 4).text())
                self.total_price.setText("{:.2f}".format(total_price))
                self.total_price.setAlignment(QtCore.Qt.AlignRight)
        self.BP.barcode = []

if __name__ == "__main__":
    # global date_data, history_data
    print 'main.........................................'
    ft = firebase_thread().start()
    with open('db/ItemList.csv','r') as f:
        print f
        for line in f:
            print line
            line_split = line.strip().split(',')
            (barcode,name,price,stock) = line_split
            items = items_info.copy()
            items['Barcode'] = barcode
            items['Item Name'] = unicode(name, "utf-8")
            items['Price'] = price
            items['Stock'] = stock
            # print items
            items_list.append(items)

            # print items_list

    # json_data = open('db/data.json').read()
    # date_data = json.loads(json_data)

    with open('db/data.json') as f:
        date_data = json.load(f)
        # print date_data

    curr_date_str = datetime.datetime.now().strftime("%Y%m%d")
    print curr_date_str

    if os.path.exists('db/history/' + curr_date_str + '.json'):
        json_data=open('db/history/' + curr_date_str + '.json').read()
        history_data = json.loads(json_data)

        # print history_data

    
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
