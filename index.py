from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.uic import loadUiType
from PyQt5 import uic
import pandas as pd
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Image,
    Table,
    TableStyle,
    Spacer,
    Paragraph,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.platypus.doctemplate import PageTemplate, Frame
from reportlab.lib.units import inch
from PyQt5.QtGui import QPixmap, QPainter
import time
from os import path
import os
import math
import sys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QColorDialog,
)
from PyQt5.QtCore import Qt, QTimer
from pyqtgraph import LegendItem

FORM_CLASS, _ = loadUiType(path.join(path.dirname(__file__), "signal_viewer.ui"))


class Signal:
    def __init__(self, path, color="blue", title="Signal", channel="channel1"):
        self.path = path
        self.color = color
        self.title = title
        self.current_channel = channel

class Channel(pg.PlotWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.signal_data = []  # Store multiple signal data
        self.plot_items = []
        self.snapshots=[] #to store taken snapshots 
        
        self.legend = self.addLegend(offset=(70, 30))
        # Store multiple plot items for each signal
        self.colors = ["green", "blue", "red", "cyan", "magenta", "yellow", "white"]
        self.color_index = 0
        self.setLabel("left", "Amplitude")
        self.setLabel("bottom", "Time")
        self.setTitle("Signal Viewer")
        self.enableAutoRange("xy")
        self.data_index = 0
        self.XMin = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_graph)
        self.timer_interval = 100  # Update interval in milliseconds
        self.timer.start(self.timer_interval)
        self.playing = True
        self.speed_multiplier = 1
        self.current_zoom = 1.0
        self.max_zoom_factor = 2.0
        self.min_zoom_factor = 1.0
        self.getViewBox().setLimits(xMin=0)
        self.getViewBox().setLimits(yMin=0)
        



    def update_graph(self):
        if self.playing:
            self.update_signal()


    def load_signal(self, file_path, title):
        new_signal_data = np.loadtxt(file_path, delimiter=",", skiprows=1)
        self.signal_data.append(new_signal_data)  
        self.data_index = 0
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        plot_item = self.plot(pen=color)
        self.plot_items.append(plot_item)
        
        y_min = np.min(new_signal_data[:, 1]) * 2
        y_max = np.max(new_signal_data[:, 1]) * 2
        # Set the Y-axis limits for the viewbox
        self.getViewBox().setLimits(yMin=y_min, yMax=y_max)

    def load_signal_from_data(self, signal_data, title,color):
        self.signal_data.append(signal_data)
        self.data_index = 0
        plot_item = self.plot(pen=color)
        self.plot_items.append(plot_item)
        self.channel_title = title  
        y_min = np.min(signal_data[:, 1]) * 2
        y_max = np.max(signal_data[:, 1]) * 2
        # Set the Y-axis limits for the viewbox
        self.getViewBox().setLimits(yMin=y_min, yMax=y_max)

    def update_signal(self):
        if self.signal_data:
            if self.data_index  >= len(self.signal_data[0]):
                self.data_index = 0
            for i, plot_item in enumerate(self.plot_items):
                data_chunk = self.signal_data[i][: self.data_index]
                plot_item.setData(data_chunk)
                x_values=[sublist[0] for sublist in self.signal_data[0]]
                one_sec_indecation=0
                for index,value in enumerate(x_values):
                    if value>=1:
                        one_sec_indecation=index
                        break
                            
            if self.data_index <= one_sec_indecation:
                self.setXRange(self.XMin, 1)
            else:
                self.setXRange(
                    (x_values[self.data_index] - 1)/self.current_zoom,
                    (x_values[self.data_index])/self.current_zoom)
                self.getViewBox().setLimits(xMin=0, xMax=x_values[self.data_index]/self.current_zoom+0.1)
            self.data_index += 1
            
    def increase_speed(self):
        self.speed_multiplier += 1.5
        self.timer_interval = int(100 / self.speed_multiplier)
        self.timer.start(self.timer_interval)

    def decrease_speed(self):
        if self.speed_multiplier > 0.1:
            self.speed_multiplier -= 1.5
            if self.speed_multiplier>0:
                self.timer_interval = int(100 / self.speed_multiplier)
                self.timer.start(self.timer_interval)
    
    def zoom_in(self):
        zoom_factor = 1.0 / 1.2
        if self.current_zoom < self.max_zoom_factor:
            self.getViewBox().scaleBy((zoom_factor, zoom_factor))
            self.current_zoom += 0.25

    def zoom_out(self):
        zoom_factor = 1.2
        if self.current_zoom > self.min_zoom_factor:
            self.getViewBox().scaleBy((zoom_factor, zoom_factor))
            self.current_zoom -= 0.25


    def toggle_play_pause(self):
        self.playing = not self.playing
        if self.playing:
            self.timer.start(self.timer_interval)
        else:
            self.timer.stop()
    def take_snapshots(self,flag=False):
        if self.plot_items:
            if  not flag:
                QMessageBox.information(
                    self,
                    "snapshot",
                    "snapshot taken sucessfully",
                )
            pixmap = QPixmap(self.size())
            painter = QPainter(pixmap)
            self.render(painter)
            painter.end()

            snapshot_file = f"{self.name}_{len(self.snapshots)+1}_snapshot.png"
            pixmap.save(snapshot_file, "PNG")
            self.snapshots.append(snapshot_file)
        else:
            if   not flag:
                QMessageBox.warning(
                    self,"warning","empty channel!"
                )
            
    def create_pdf(self):
        if not self.signal_data:
            QMessageBox.warning(
                self,
                "Empty Channel",
                f"{self.name} does not have any signals. Unable to create a PDF.",
            )
            return  

        pdf_file = f"signal_snapshots_{self.name}.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []
        header_style = ParagraphStyle(
            name="HeaderStyle", parent=styles["Heading1"], fontSize=14, alignment=1
        )

        def header(canvas, doc):
            canvas.saveState()
            header_text = Paragraph(f"{self.name} Report", header_style)
            w, h = header_text.wrap(doc.width, doc.topMargin)
            header_text.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h)
            canvas.restoreState()

        frame = Frame(
            doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal"
        )
        template = PageTemplate(id="test", frames=frame)
        template.beforeDrawPage = header
        doc.addPageTemplates([template])
        elements.append(Spacer(1, 50))
        for snapshot_file in self.snapshots:
            image = Image(
                snapshot_file, width=letter[0], height=letter[1], kind="proportional")
            elements.append(image)
            elements.append(Spacer(1, 30))
        signal_stats = []
        for j, signal_data in enumerate(self.signal_data):
            signal_mean = np.mean(signal_data)
            signal_stdev = np.std(signal_data)
            signal_stats.append(
                [f"Signal {j + 1}", f"{signal_mean:.2f}", f"{signal_stdev:.2f}"]
            )

        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )

        elements.append(Spacer(1, 10))
        table_data = [["Signal", "Mean", "St Deviation"]]
        table_data.extend(signal_stats)
        table = Table(table_data, colWidths=[150, 70, 70])
        table.setStyle(table_style)
        elements.append(table)

        doc.build(elements)
        QMessageBox.information(
            self,
            "PDF Created",
            "Signal snapshots and statistics saved to signal_snapshots.pdf",
        )

class MainApp(QMainWindow, FORM_CLASS):
    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)
        self.setGeometry(0, 0, 1920, 1080)
        self.setWindowTitle("Signal Viewer")
        self.setupUi(self)

        self.viewer_layout = QVBoxLayout(self.viewer_widget)

        self.viewer1 = Channel('Channel 1')
        self.viewer2 = Channel('Channel 2')
        label_2=QLabel()
        self.viewer_layout.addWidget(self.label_2)
        self.viewer_layout.addWidget(self.viewer1)
        widgetleft=QWidget()
        self.viewer_layout.addWidget(self.widgetleft)
        label=QLabel()
        self.viewer_layout.addWidget(self.label)
        self.viewer_layout.addWidget(self.viewer2)
        
        self.snapshot_1.clicked.connect(self.viewer1.take_snapshots)
        self.snapshot_2.clicked.connect(self.viewer2.take_snapshots)
        self.snapshot_3.clicked.connect(self.take_snapshots3)

        self.add_signal_channel1_button.triggered.connect(self.load_signal1)
        self.add_signal_channel2_button.triggered.connect(self.load_signal2)

        self.actionexit.triggered.connect(self.exit_program)

        self.channel_1_edit_confirm.clicked.connect(self.edit_signal_name1)
        self.channel_2_edit_confirm.clicked.connect(self.edit_signal_name2)

        self.adjust_color_channel1_button.clicked.connect(self.adjust_color_channel1)
        self.adjust_color_channel2_button.clicked.connect(self.adjust_color_channel2)
        self.adjust_color_channel2_button.setStyleSheet("background-color : #ffffff")
        self.adjust_color_channel1_button.setStyleSheet("background-color : #ffffff")

        self.playBtn1.clicked.connect(self.toggle_play_pause1)
        self.pauseBtn1.clicked.connect(self.toggle_play_pause1)

        self.playBtn2.clicked.connect(self.toggle_play_pause2)
        self.pauseBtn2.clicked.connect(self.toggle_play_pause2)

        self.playBtn3.clicked.connect(self.toggle_play_pause3)
        self.pauseBtn3.clicked.connect(self.toggle_play_pause3)

        self.SpeedUp1.clicked.connect(self.viewer1.increase_speed)
        self.slowdownBtn1.clicked.connect(self.viewer1.decrease_speed)

        self.SpeedUp2.clicked.connect(self.viewer2.increase_speed)
        self.slowdownBtn2.clicked.connect(self.viewer2.decrease_speed)

        self.SpeedUp3.clicked.connect(self.increase_speed3)
        self.slowdownBtn3.clicked.connect(self.decrease_speed3)

        self.zoom_in_btn1.clicked.connect(self.viewer1.zoom_in)
        self.zoom_out_btn1.clicked.connect(self.viewer1.zoom_out)

        self.zoom_in_btn2.clicked.connect(self.viewer2.zoom_in)
        self.zoom_out_btn2.clicked.connect(self.viewer2.zoom_out)

        self.zoom_in_btn3.clicked.connect(self.zoom_in3)
        self.zoom_out_btn3.clicked.connect(self.zoom_out3)

        self.export_channel1_btn.triggered.connect(self.viewer1.create_pdf)
        self.export_channel2_btn.triggered.connect(self.viewer2.create_pdf)
        self.export_channel12_btn.triggered.connect(self.create_pdf3)

        self.rewind_btn1.clicked.connect(self.rewind_viewer1)
        self.rewind_btn2.clicked.connect(self.rewind_viewer2)
        self.rewind_btn3.clicked.connect(self.rewind_viewer3)
        
        self.channel_1_combobox.currentIndexChanged.connect(self.update_color_1)
        self.channel_2_combobox.currentIndexChanged.connect(self.update_color_2)

        self.channel_1_hide_checkbox.stateChanged.connect(
            self.toggle_signal_visibility1
        )

        # self.channel_1_combobox.currentIndexChanged.connect(self.update_checkbox1)

        self.channel_2_hide_checkbox.stateChanged.connect(
            self.toggle_signal_visibility2
        )

        # self.channel_2_combobox.currentIndexChanged.connect(self.update_checkbox2)

        self.is_active = False
        self.wholewidget.show()
        self.set_inactive()
        self.Linkbutton.clicked.connect(self.toggle_behavior_link)

        self.playBtn1.hide()
        self.playBtn2.hide()
        self.playBtn3.hide()

        self.move_to_channel1_button.clicked.connect(self.move_signal_to_channel1)
        self.move_to_channel2_button.clicked.connect(self.move_signal_to_channel2)
    def take_snapshots3(self):
        if self.viewer1.plot_items and self.viewer2.plot_items:
            self.viewer1.take_snapshots()
            self.viewer2.take_snapshots(True)
        else :
            QMessageBox.warning (self,"warning","one of the channels is empty  ")
    def create_pdf3(self):
        # Check if both channels are empty
        if not self.viewer1.signal_data and not self.viewer2.signal_data:
            QMessageBox.warning(
                self,
                "Empty Channels",
                "Both Channel 1 and Channel 2 do not have any signals. Unable to create PDFs.",
            )
            return  # Exit the function

        # Check if Channel 1 is empty
        if not self.viewer1.signal_data:
            QMessageBox.warning(
                self,
                "Empty Channel",
                "Channel 1 does not have any signals. Unable to create a PDF for Channel 1.",
            )
            return
        # Check if Channel 2 is empty
        if not self.viewer2.signal_data:
            QMessageBox.warning(
                self,
                "Empty Channel",
                "Channel 2 does not have any signals. Unable to create a PDF for Channel 2.",
            )
            return
        # Create a PDF file
        pdf_file = "signal_snapshots_channel_1_and_2.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []
        header_style = ParagraphStyle(
            name="HeaderStyle", parent=styles["Heading1"], fontSize=18, alignment=1
        )

        # Define a custom PageTemplate for the header

        frame = Frame(
            doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal"
        )
        template = PageTemplate(id="test", frames=frame)

        # template.beforeDrawPage = header

        doc.addPageTemplates([template])
        # Create snapshots of signals and add to PDF
        for i, viewer in enumerate([self.viewer1, self.viewer2]):
            # Add the header title for this page
            centered_text = Paragraph(f"Channel {i+1} Report", header_style)

            elements.append(centered_text)
            elements.append(Spacer(1, 30))

            elements.append(Spacer(1, 50))
            # Render the viewer widget to an image
            for snapshot_file in viewer.snapshots:
                image = Image(
                    snapshot_file, width=letter[0], height=letter[1], kind="proportional")
                elements.append(image)
                elements.append(Spacer(1, 30))
                # Calculate statistics for each signal using NumPy
            signal_stats = []
            for j, signal_data in enumerate(viewer.signal_data):
                signal_mean = np.mean(signal_data)
                signal_stdev = np.std(signal_data)
                signal_stats.append(
                    [f"Signal {j + 1}", f"{signal_mean:.2f}", f"{signal_stdev:.2f}"]
                )

            # Create a table style to customize the appearance of the table
            table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )

            # Add a table to the PDF with signal statistics and apply the custom style
            elements.append(Spacer(1, 10))
            table_data = [["Signal", "Mean", "St Deviation"]]
            table_data.extend(signal_stats)
            table = Table(table_data, colWidths=[150, 70, 70])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(PageBreak())

        doc.build(elements)
        QMessageBox.information(
            self,
            "PDF Created",
            "Signal snapshots and statistics saved to signal_snapshots.pdf",
        )

    def set_inactive(self):
        self.widget_5.hide()
        self.widgetleft.show()
        self.widgetright.show()
        self.rewind_btn1.show()
        self.rewind_btn2.show()
        self.rewind_btn3.hide()
        self.Linkbutton.setStyleSheet(
            "QPushButton{background-color:#005086; border-radius:5px ; }"
        )

    def set_active(self):
        self.viewer1.playing = True
        self.viewer2.playing = True
        self.viewer1.timer_interval = 100
        self.viewer2.timer_interval = 100
        self.viewer1.timer.start(self.viewer1.timer_interval)
        self.viewer2.timer.start(self.viewer2.timer_interval)
        self.viewer1.speed_multiplier = 1
        self.viewer2.speed_multiplier = 1

        self.widget_5.show()
        self.widgetleft.hide()
        self.widgetright.hide()
        self.rewind_btn1.hide()
        self.rewind_btn2.hide()
        self.rewind_btn3.show()

        self.Linkbutton.setStyleSheet(
            "QPushButton{background-color:#FF0000; border-radius:5px ; }"
        )

    def toggle_behavior_link(self):
        if self.is_active:
            self.set_inactive()
        else:
            self.set_active()
        self.is_active = not self.is_active
            
    def load_signal1(self):
        file_path,_ = QFileDialog.getOpenFileName(
            self,
            "Open Signal 1",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if file_path:
            title = os.path.basename(file_path)   # Set the title automatically
            if title:
                if self.is_name_unique(title, self.channel_1_combobox):
                    self.viewer1.load_signal(file_path, title)
                    self.channel_1_combobox.addItem(title[:-4])
                    self.viewer1.legend.addItem(self.viewer1.plot_items[-1], title[:-4])
                    self.channel_1_hide_checkbox.setChecked(Qt.Checked)
                    # Set the button's color to match the initial color
                    # last_plot_item = self.viewer1.plot_items[-1]
                    # initial_color = last_plot_item.opts["pen"].color()
                    # button_stylesheet = f"background-color: {initial_color.name()}"
                    # self.adjust_color_channel1_button.setStyleSheet(button_stylesheet)
                else:
                    QMessageBox.warning(
                        self,
                        "Duplicate Name",
                        "The name already exists in the combo box. Please use a unique name.",
                    )


    def load_signal2(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Signal 2",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if file_path:
            title = os.path.basename(file_path)  # Set the title automatically
            if title:
                if self.is_name_unique(title, self.channel_2_combobox):
                    self.viewer2.load_signal(file_path, title)
                    self.channel_2_combobox.addItem(title[:-4])
                    self.viewer2.legend.addItem(self.viewer2.plot_items[-1], title[:-4])
                    self.channel_2_hide_checkbox.setChecked(Qt.Checked)
                else:
                    QMessageBox.warning(
                        self,
                        "Duplicate Name",
                        "The name already exists in the combo box. Please use a unique name.",
                    )

    def is_name_unique(self, name, combo_box):
        for i in range(combo_box.count()):
            if name == combo_box.itemText(i):
                return False
        return True

    def toggle_play_pause1(self):
        self.viewer1.toggle_play_pause()
        if self.viewer1.playing:
            self.pauseBtn1.show()
            self.playBtn1.hide()
        else:
            self.pauseBtn1.hide()
            self.playBtn1.show()

    def toggle_play_pause2(self):
        self.viewer2.toggle_play_pause()
        if self.viewer2.playing:
            self.pauseBtn2.show()
            self.playBtn2.hide()
        else:
            self.pauseBtn2.hide()
            self.playBtn2.show()

    def toggle_play_pause3(self):
        self.viewer1.toggle_play_pause()
        self.viewer2.toggle_play_pause()
        if self.viewer1.playing:
            self.pauseBtn3.show()
            self.playBtn3.hide()
        else:
            self.pauseBtn3.hide()
            self.playBtn3.show()

    def increase_speed3(self):
        self.viewer1.increase_speed()
        self.viewer2.increase_speed()

    def decrease_speed3(self):
        self.viewer1.decrease_speed()
        self.viewer2.decrease_speed()

    def zoom_in3(self):
        self.viewer1.zoom_in()
        self.viewer2.zoom_in()

    def zoom_out3(self):
        self.viewer1.zoom_out()
        self.viewer2.zoom_out()

    def rewind_viewer1(self):
        self.viewer1.data_index = 0
        self.viewer1.update_signal() 

    def rewind_viewer2(self):
        self.viewer2.data_index = 0
        self.viewer2.update_signal()  

    def rewind_viewer3(self):
        self.rewind_viewer1()
        self.rewind_viewer2()

    def edit_signal_name1(self):
        new_name = self.channel_1_edit_line_edit.text()
        selected_index = self.channel_1_combobox.currentIndex()
        selected_text=self.channel_1_combobox.currentText()
        if selected_index >= 0 and new_name:
            existing_names = [
                self.channel_1_combobox.itemText(i)
                for i in range(self.channel_1_combobox.count())
            ]
            if new_name in existing_names:
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    "The name already exists in the combo box. Please use a unique name.",
                )
                self.channel_1_edit_line_edit.clear()
            else:
                self.channel_1_combobox.setItemText(selected_index, new_name)
                self.viewer1.legend.removeItem(selected_text)
                self.viewer1.legend.addItem(self.viewer1.plot_items[selected_index], new_name)
                self.channel_1_edit_line_edit.clear()
                                
    def edit_signal_name2(self):
        new_name = self.channel_2_edit_line_edit.text()
        selected_index = self.channel_2_combobox.currentIndex()
        selected_text=self.channel_2_combobox.currentText()
        if selected_index >= 0 and new_name:
            existing_names = [
                self.channel_2_combobox.itemText(i)
                for i in range(self.channel_2_combobox.count())
            ]
            if new_name in existing_names:
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    "The name already exists in the combo box. Please use a unique name.",
                )
                self.channel_2_edit_line_edit.clear()
            else:
                self.channel_2_combobox.setItemText(selected_index, new_name)
                self.viewer2.legend.removeItem(selected_text)
                self.viewer2.legend.addItem(self.viewer2.plot_items[selected_index], new_name)
                self.viewer2.setLabel("bottom", new_name)  # Update the signal title
                self.channel_2_edit_line_edit.clear()

    def adjust_color_channel1(self):
        selected_index = self.channel_1_combobox.currentIndex()
        if selected_index >= 0:
            color = QColorDialog.getColor()
            if color.isValid():
                new_color = color.name()
                if selected_index < len(self.viewer1.plot_items):
                    self.viewer1.plot_items[selected_index].setPen(new_color)
                    # Update the button color
                    button_stylesheet = f"background-color: {new_color}"
                    self.adjust_color_channel1_button.setStyleSheet(button_stylesheet)

    def adjust_color_channel2(self):
        selected_index = self.channel_2_combobox.currentIndex()
        if selected_index >= 0:
            color = QColorDialog.getColor()
            if color.isValid():
                new_color = color.name()
                if selected_index < len(self.viewer2.plot_items):
                    self.viewer2.plot_items[selected_index].setPen(new_color)
                    # Update the button color
                    button_stylesheet = f"background-color: {new_color}"
                    self.adjust_color_channel2_button.setStyleSheet(button_stylesheet)

    def toggle_signal_visibility1(self, state):
        if state == Qt.Checked:
            selected_index = self.channel_1_combobox.currentIndex()
            if selected_index >= 0:
                item_text = self.channel_1_combobox.currentText()
                self.channel_1_combobox.setItemText(
                    selected_index, item_text.replace(" (hidden)", "")
                )
                self.viewer1.plot_items[selected_index].show()
        else:
            selected_index = self.channel_1_combobox.currentIndex()
            if selected_index >= 0:
                item_text = self.channel_1_combobox.currentText()
                self.channel_1_combobox.setItemText(
                    selected_index, f"{item_text} (hidden)"
                )
                self.viewer1.plot_items[selected_index].hide()
        

    def toggle_signal_visibility2(self, state):
        if state == Qt.Checked:
            selected_index = self.channel_2_combobox.currentIndex()
            if selected_index >= 0:
                item_text = self.channel_2_combobox.currentText()
                self.channel_2_combobox.setItemText(
                    selected_index, item_text.replace(" (hidden)", "")
                )
                self.viewer2.plot_items[selected_index].show()
        else:
            selected_index = self.channel_2_combobox.currentIndex()
            if selected_index >= 0:
                item_text = self.channel_2_combobox.currentText()
                self.channel_2_combobox.setItemText(
                    selected_index, f"{item_text} (hidden)"
                )
                self.viewer2.plot_items[selected_index].hide()
      

    def update_checkbox1(self, index):
        if index >= 0:
            item_text = self.channel_1_combobox.currentText()
            if "(hidden)" in item_text:
                self.channel_1_hide_checkbox.setChecked(Qt.Checked)
            else:
                self.channel_1_hide_checkbox.setChecked(Qt.Unchecked)

    def update_checkbox2(self, index):
        if index >= 0:
            item_text = self.channel_2_combobox.currentText()
            if "(hidden)" in item_text:
                self.channel_2_hide_checkbox.setChecked(Qt.Checked)
            else:
                self.channel_2_hide_checkbox.setChecked(Qt.Unchecked)

    def move_signal_to_channel1(self):
        selected_signal_index = self.channel_2_combobox.currentIndex()
        if selected_signal_index >= 0:
            signal_name = self.channel_2_combobox.itemText(selected_signal_index)
            if self.is_name_unique(signal_name, self.channel_1_combobox):
                signal_data = self.viewer2.signal_data[selected_signal_index]
                title = self.channel_2_combobox.currentText()
                button = self.adjust_color_channel2_button  

                # # Get the background color of the button
                palette = button.palette()
                color = palette.color(button.backgroundRole())
                color=color.name()
                self.viewer2.signal_data.pop(selected_signal_index)
                self.channel_2_combobox.removeItem(selected_signal_index)
                self.viewer1.load_signal_from_data(signal_data, title,color)
                self.channel_1_combobox.addItem(title)
                self.viewer2.removeItem(self.viewer2.plot_items[selected_signal_index])
                self.viewer2.plot_items.pop(selected_signal_index)
                self.viewer1.playing=True
                self.viewer1.legend.addItem(self.viewer1.plot_items[-1], title)
                self.update_color_1(color)
                self.update_color_2(color)
            
            else:
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    "The name already exists in Channel 1 Combobox. Please use a unique name.",
                )

    def move_signal_to_channel2(self):
        selected_signal_index = self.channel_1_combobox.currentIndex()
        if selected_signal_index >= 0:
            signal_name = self.channel_1_combobox.itemText(selected_signal_index)
            if self.is_name_unique(signal_name, self.channel_2_combobox):
                signal_data = self.viewer1.signal_data[selected_signal_index]
                title = self.channel_1_combobox.currentText()
                button = self.adjust_color_channel1_button  

                # Get the background color of the button
                palette = button.palette()
                color = palette.color(button.backgroundRole())
                color=color.name()
                self.viewer1.signal_data.pop(selected_signal_index)
                self.channel_1_combobox.removeItem(selected_signal_index)
                self.viewer2.load_signal_from_data(signal_data, title,color)
                self.channel_2_combobox.addItem(title)
                self.viewer1.removeItem(self.viewer1.plot_items[selected_signal_index])
                self.viewer1.plot_items.pop(selected_signal_index)
                self.viewer2.playing=True  
                self.viewer2.legend.addItem(self.viewer2.plot_items[-1], title)              
                self.update_color_1(color)
                self.update_color_2(color)
            else:
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    "The name already exists in Channel 2 Combobox. Please use a unique name.",
                )
         
    def update_color_1(self,color):
        if not len(self.viewer1.plot_items):
            self.adjust_color_channel1_button.setStyleSheet(f"background-color:\"white\";")
        else:
            selected_index = self.channel_1_combobox.currentIndex()
            if selected_index < len(self.viewer1.plot_items):
                pen = self.viewer1.plot_items[selected_index].opts['pen']
                self.adjust_color_channel1_button.setStyleSheet(f"background-color: {pen};")



    def update_color_2(self,color):
        if not len(self.viewer2.plot_items):
            self.adjust_color_channel2_button.setStyleSheet(f"background-color:\"white\";")
        else:
            selected_index = self.channel_2_combobox.currentIndex()
            if selected_index < len(self.viewer2.plot_items):
                pen = self.viewer2.plot_items[selected_index].opts['pen']
                self.adjust_color_channel2_button.setStyleSheet(f"background-color: {pen};")   

    def exit_program(self):
        sys.exit()

def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
