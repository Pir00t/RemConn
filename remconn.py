from PyQt6.QtWidgets import (
	QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QListWidget, 
	QPushButton, QWidget, QDialog, QFormLayout, QLineEdit, QComboBox, 
	QMessageBox, QLabel, QTabWidget, QMenu, QSystemTrayIcon, QInputDialog, QStatusBar
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QShortcut
import json
import sys
import os
import platform
import time
from subprocess import run

class ConnectionWorker(QObject):
	finished = pyqtSignal(str, bool)
	progress = pyqtSignal(str)
	
	def __init__(self, session, cmd):
		super().__init__()
		self.session = session
		self.cmd = cmd
		
	def run(self):
		self.progress.emit(f"Connecting to {self.session}...")
		try:
			if platform.system() == "Windows":
				run(self.cmd, shell=True)
			else:
				# Unix/Linux: use screen for persistent sessions
				run(["screen", "-dm", "-S", self.session], check=True)
				run(["screen", "-r", self.session, "-p", "0", "-X", "stuff", f"{self.cmd}\n"], check=True)
				
			self.finished.emit(f"Successfully connected to {self.session}", True)
		except Exception as e:
			self.finished.emit(f"Error connecting to {self.session}: {str(e)}", False)

class SSHConnectionManager(QMainWindow):
	def __init__(self, config):
		super().__init__()
		self.setWindowTitle("RemConn")
		self.config = config
		self.session_threads = {}
		self.setupUI()
		self.setupShortcuts()
		self.setupStatusBar()
		self.setupSystemTray()

		# If no categories exist, prompt user to create one
		if not self.config:
			self.promptFirstCategory()

	def promptFirstCategory(self):
		"""Prompt user to create their first category."""
		msg = QMessageBox()
		msg.setIcon(QMessageBox.Icon.Information)
		msg.setWindowTitle("Welcome")
		msg.setText("Welcome to RemConn!")
		msg.setInformativeText("Would you like to create your first category now?")
		msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
		
		if msg.exec() == QMessageBox.StandardButton.Yes:
			self.add_category_dialog()
		else:
			self.close()
		
	def setupUI(self):
		main_widget = QWidget()
		main_layout = QVBoxLayout()
		
		# Add search bar at the top
		search_layout = QHBoxLayout()
		search_label = QLabel("Search:")
		self.search_box = QLineEdit()
		self.search_box.setPlaceholderText("Filter connections...")
		self.search_box.textChanged.connect(self.filterConnections)
		search_layout.addWidget(search_label)
		search_layout.addWidget(self.search_box)
		main_layout.addLayout(search_layout)
		
		# Create tab widget for categories
		self.tab_widget = QTabWidget()
		self.tab_widget.currentChanged.connect(self.onTabChanged)
		
		# Process each category
		self.connection_lists = {}
		for category in self.config.keys():
			self.addCategoryTab(category)
		
		# Create button layout
		button_layout = QHBoxLayout()
		
		connect_btn = QPushButton("Connect")
		connect_btn.setIcon(QIcon.fromTheme("network-wired"))
		edit_btn = QPushButton("Edit Connection")
		edit_btn.setIcon(QIcon.fromTheme("document-edit"))
		add_connection_btn = QPushButton("Add Connection")
		add_connection_btn.setIcon(QIcon.fromTheme("list-add"))
		add_category_btn = QPushButton("Add Category")
		add_category_btn.setIcon(QIcon.fromTheme("folder-new"))
		save_btn = QPushButton("Save Changes")
		save_btn.setIcon(QIcon.fromTheme("document-save"))
		close_btn = QPushButton("Close")
		close_btn.setIcon(QIcon.fromTheme("application-exit"))
		
		connect_btn.clicked.connect(self.connect)
		edit_btn.clicked.connect(self.editSelectedConnection)
		add_connection_btn.clicked.connect(self.add_connection_dialog)
		add_category_btn.clicked.connect(self.add_category_dialog)
		save_btn.clicked.connect(lambda: self.save_config("config.json"))
		close_btn.clicked.connect(self.close)
		
		button_layout.addWidget(connect_btn)
		button_layout.addWidget(edit_btn)
		button_layout.addWidget(add_connection_btn)
		button_layout.addWidget(add_category_btn)
		button_layout.addWidget(save_btn)
		button_layout.addWidget(close_btn)
		
		# Assemble layout
		main_layout.addWidget(self.tab_widget)
		main_layout.addLayout(button_layout)
		main_widget.setLayout(main_layout)
		self.setCentralWidget(main_widget)
		
		# Set window size
		self.resize(600, 400)
	
	def setupShortcuts(self):
		# Connect shortcut
		self.shortcut_connect = QShortcut(QKeySequence("Return"), self)
		self.shortcut_connect.activated.connect(self.connect)
		
		# Save shortcut
		self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
		self.shortcut_save.activated.connect(lambda: self.save_config("config.json"))
		
		# Add connection shortcut
		self.shortcut_add = QShortcut(QKeySequence("Ctrl+N"), self)
		self.shortcut_add.activated.connect(self.add_connection_dialog)
		
		# Edit connection shortcut
		self.shortcut_edit = QShortcut(QKeySequence("Ctrl+E"), self)
		self.shortcut_edit.activated.connect(self.editSelectedConnection)
		
		# Delete connection shortcut
		self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
		self.shortcut_delete.activated.connect(self.deleteSelectedConnection)
	
	def setupStatusBar(self):
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)
		self.statusBar.showMessage("Ready", 3000)
	
	def setupSystemTray(self):
		self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("network-server"), self)
		tray_menu = QMenu()
		
		# Add common actions
		show_action = QAction("Show", self)
		quit_action = QAction("Exit", self)
		show_action.triggered.connect(self.show)
		quit_action.triggered.connect(self.close)
		tray_menu.addAction(show_action)
		tray_menu.addSeparator()
		tray_menu.addAction(quit_action)
		
		self.tray_icon.setContextMenu(tray_menu)
		self.tray_icon.activated.connect(self.onTrayIconActivated)
		self.tray_icon.show()
	
	def onTrayIconActivated(self, reason):
		if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
			self.show()
	
	def addCategoryTab(self, category):
		category_widget = QWidget()
		category_layout = QVBoxLayout()
		
		# Create list widget for this category
		list_widget = self.create_list_widget(list(self.config[category].keys()))
		self.connection_lists[category] = list_widget
		
		# Enable double-click to connect
		list_widget.itemDoubleClicked.connect(self.connectToSelected)
		
		# Enable context menu
		list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		list_widget.customContextMenuRequested.connect(
			lambda pos, lw=list_widget: self.showContextMenu(pos, lw)
		)
		
		category_layout.addWidget(list_widget)
		category_widget.setLayout(category_layout)
		self.tab_widget.addTab(category_widget, category)
	
	def create_list_widget(self, items):
		"""Create a QListWidget for SSH connections."""
		widget = QListWidget()
		widget.addItems(items)
		return widget
	
	def get_current_category(self):
		"""Get the currently selected category tab."""
		return self.tab_widget.tabText(self.tab_widget.currentIndex())
	
	def onTabChanged(self):
		"""Handle tab change by updating the search filter."""
		self.filterConnections(self.search_box.text())
	
	def filterConnections(self, text):
		"""Filter connections based on search text."""
		current_category = self.get_current_category()
		if current_category not in self.connection_lists:
			return
			
		current_list = self.connection_lists[current_category]
		
		if not text:
			# Show all items if no search text
			for i in range(current_list.count()):
				current_list.item(i).setHidden(False)
		else:
			# Show only matching items
			for i in range(current_list.count()):
				item = current_list.item(i)
				item.setHidden(text.lower() not in item.text().lower())
	
	def showContextMenu(self, position, list_widget):
		"""Show context menu for list items."""
		menu = QMenu()
		connect_action = menu.addAction("Connect")
		edit_action = menu.addAction("Edit")
		delete_action = menu.addAction("Delete")
		
		# Only enable actions if an item is selected
		item = list_widget.itemAt(position)
		if not item:
			connect_action.setEnabled(False)
			edit_action.setEnabled(False)
			delete_action.setEnabled(False)
		
		action = menu.exec(list_widget.mapToGlobal(position))
		
		if not item:
			return
			
		if action == connect_action:
			self.connectToSelected(item)
		elif action == edit_action:
			self.editConnection(item.text(), self.get_current_category())
		elif action == delete_action:
			self.deleteConnection(item.text(), self.get_current_category())
	
	def connectToSelected(self, item):
		"""Handle double-click to connect."""
		current_category = self.get_current_category()
		if item.text() in self.config[current_category]:
			self.connectToSession(item.text(), current_category)
	
	def connect(self):
		"""Handle connecting to selected connection(s)."""
		current_category = self.get_current_category()
		current_list = self.connection_lists[current_category]
		
		# Use index.row() to get the actual row number from QModelIndex
		selected_items = [current_list.item(index.row()).text() 
						 for index in current_list.selectedIndexes()]
		
		if not selected_items:
			QMessageBox.warning(self, "No Selection", "Please select a connection.")
			return
		
		for session in selected_items:
			self.connectToSession(session, current_category)
	
	def connectToSession(self, session, category):
		"""Connect to a specific session using a worker thread."""
		if session not in self.config[category]:
			QMessageBox.critical(
				self, "Configuration Error", 
				f"Session '{session}' not found in {category} configuration."
			)
			return
		
		cmd = self.config[category][session]["cmd"]
		
		# Create worker and thread
		self.thread = QThread()
		self.worker = ConnectionWorker(session, cmd)
		self.worker.moveToThread(self.thread)
		
		# Connect signals
		self.thread.started.connect(self.worker.run)
		self.worker.finished.connect(self.onConnectionFinished)
		self.worker.progress.connect(self.onConnectionProgress)
		self.worker.finished.connect(self.thread.quit)
		self.worker.finished.connect(self.worker.deleteLater)
		self.thread.finished.connect(self.thread.deleteLater)
		
		# Start the thread
		self.thread.start()
		
		# Store thread reference
		self.session_threads[session] = self.thread
		
		# Update status
		self.statusBar.showMessage(f"Connecting to {session}...")
	
	def onConnectionProgress(self, message):
		"""Handle connection progress updates."""
		self.statusBar.showMessage(message)
	
	def onConnectionFinished(self, message, success):
		"""Handle connection completion."""
		if success:
			self.statusBar.showMessage(message, 5000)
		else:
			self.statusBar.showMessage(message, 10000)
			QMessageBox.warning(self, "Connection Issue", message)
	
	def editSelectedConnection(self):
		"""Edit the currently selected connection."""
		current_category = self.get_current_category()
		current_list = self.connection_lists[current_category]
		
		selected_items = current_list.selectedItems()
		if not selected_items:
			QMessageBox.warning(self, "No Selection", "Please select a connection to edit.")
			return
		
		# Edit the first selected item
		self.editConnection(selected_items[0].text(), current_category)
	
	def editConnection(self, connection_name, category):
		"""Open dialog to edit an existing connection."""
		if connection_name not in self.config[category]:
			QMessageBox.critical(self, "Error", f"Connection '{connection_name}' not found.")
			return
		
		dialog = QDialog(self)
		dialog.setWindowTitle(f"Edit Connection: {connection_name}")
		
		layout = QFormLayout()
		
		# Pre-fill with existing values
		category_combo = QComboBox()
		for i in range(self.tab_widget.count()):
			category_combo.addItem(self.tab_widget.tabText(i))
		category_combo.setCurrentText(category)
		
		conn_name = QLineEdit(connection_name)
		cmd = QLineEdit(self.config[category][connection_name]["cmd"])
		
		layout.addRow("Category:", category_combo)
		layout.addRow("Name:", conn_name)
		layout.addRow("Command:", cmd)
		
		def update_connection():
			"""Update the connection with new values."""
			new_category = category_combo.currentText()
			new_name = conn_name.text()
			new_cmd = cmd.text()
			
			if not new_name or not new_cmd:
				QMessageBox.critical(dialog, "Error", "All fields are required.")
				return
			
			# Handle category change
			if new_category != category:
				# Remove from old category
				del self.config[category][connection_name]
				
				# Update list widgets
				for i in range(self.connection_lists[category].count()):
					if self.connection_lists[category].item(i).text() == connection_name:
						self.connection_lists[category].takeItem(i)
						break
				
				# Ensure new category exists
				if new_category not in self.config:
					self.config[new_category] = {}
					self.addCategoryTab(new_category)
			elif new_name != connection_name:
				# Just remove the old name if it's changing within same category
				del self.config[category][connection_name]
				
				# Update list widget
				for i in range(self.connection_lists[category].count()):
					if self.connection_lists[category].item(i).text() == connection_name:
						self.connection_lists[category].takeItem(i)
						break
			
			# Add with new values
			if new_category not in self.config:
				self.config[new_category] = {}
			
			self.config[new_category][new_name] = {"cmd": new_cmd}
			
			# Update the list widget for the new category
			if new_category in self.connection_lists:
				# Only add if it doesn't already exist
				items = [self.connection_lists[new_category].item(i).text() 
						 for i in range(self.connection_lists[new_category].count())]
				if new_name not in items:
					self.connection_lists[new_category].addItem(new_name)
				
			QMessageBox.information(dialog, "Success", f"Updated connection '{new_name}'.")
			dialog.accept()
		
		# Add buttons
		button_layout = QHBoxLayout()
		update_btn = QPushButton("Update")
		cancel_btn = QPushButton("Cancel")
		
		update_btn.clicked.connect(update_connection)
		cancel_btn.clicked.connect(dialog.reject)
		
		button_layout.addWidget(update_btn)
		button_layout.addWidget(cancel_btn)
		
		layout.addRow("", button_layout)
		dialog.setLayout(layout)
		dialog.exec()
	
	def deleteSelectedConnection(self):
		"""Delete the currently selected connection."""
		current_category = self.get_current_category()
		current_list = self.connection_lists[current_category]
		
		selected_items = current_list.selectedItems()
		if not selected_items:
			QMessageBox.warning(self, "No Selection", "Please select a connection to delete.")
			return
		
		# Delete the first selected item
		self.deleteConnection(selected_items[0].text(), current_category)
	
	def deleteConnection(self, connection_name, category):
		"""Delete a connection from configuration and UI."""
		if connection_name not in self.config[category]:
			QMessageBox.critical(self, "Error", f"Connection '{connection_name}' not found.")
			return
		
		reply = QMessageBox.question(
			self, "Confirm Deletion",
			f"Are you sure you want to delete connection '{connection_name}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
		)
		
		if reply == QMessageBox.StandardButton.Yes:
			# Remove from config
			del self.config[category][connection_name]
			
			# Remove from list widget
			for i in range(self.connection_lists[category].count()):
				if self.connection_lists[category].item(i).text() == connection_name:
					self.connection_lists[category].takeItem(i)
					break
					
			self.statusBar.showMessage(f"Deleted connection '{connection_name}'", 3000)
			
			# If category is empty, ask if user wants to delete it
			if not self.config[category]:
				self.promptDeleteEmptyCategory(category)
	
	def promptDeleteEmptyCategory(self, category):
		"""Ask user if they want to delete an empty category."""
		if category in ['Lab', 'Tools']:  # Don't delete default categories
			return
			
		reply = QMessageBox.question(
			self, "Empty Category",
			f"Category '{category}' is now empty. Do you want to delete it?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
		)
		
		if reply == QMessageBox.StandardButton.Yes:
			# Remove category from config
			del self.config[category]
			
			# Remove tab
			for i in range(self.tab_widget.count()):
				if self.tab_widget.tabText(i) == category:
					self.tab_widget.removeTab(i)
					break
					
			# Remove from connection lists
			if category in self.connection_lists:
				del self.connection_lists[category]
				
			self.statusBar.showMessage(f"Deleted empty category '{category}'", 3000)
	
	def add_connection_dialog(self):
		"""Open a dialog to add a new connection."""
		dialog = QDialog(self)
		dialog.setWindowTitle("Add Connection")
		
		layout = QFormLayout()
		
		# Category dropdown with existing categories
		category_combo = QComboBox()
		for i in range(self.tab_widget.count()):
			category_combo.addItem(self.tab_widget.tabText(i))
		
		conn_name = QLineEdit()
		cmd = QLineEdit()
		
		layout.addRow("Category:", category_combo)
		layout.addRow("Name:", conn_name)
		layout.addRow("Command:", cmd)
		
		def add_connection():
			"""Add the new connection to the list and update config."""
			category = category_combo.currentText()
			name = conn_name.text()
			command = cmd.text()
			
			if not name or not command:
				QMessageBox.critical(dialog, "Error", "All fields are required.")
				return
				
			# Check for duplicate names
			if category in self.config and name in self.config[category]:
				reply = QMessageBox.question(
					dialog, "Duplicate Connection",
					f"Connection '{name}' already exists in category '{category}'. Overwrite?",
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
				)
				
				if reply != QMessageBox.StandardButton.Yes:
					return
			
			# Add to the configuration dictionary
			if category not in self.config:
				self.config[category] = {}
				self.addCategoryTab(category)
			
			self.config[category][name] = {"cmd": command}
			
			# Update the list widget - handles dynamic addition
			if category in self.connection_lists:
				items = [self.connection_lists[category].item(i).text() 
						 for i in range(self.connection_lists[category].count())]
				if name not in items:
					self.connection_lists[category].addItem(name)
			
			self.statusBar.showMessage(f"Added connection '{name}' to category '{category}'", 3000)
			dialog.accept()
		
		# Add buttons
		button_layout = QHBoxLayout()
		add_btn = QPushButton("Add")
		cancel_btn = QPushButton("Cancel")
		
		add_btn.clicked.connect(add_connection)
		cancel_btn.clicked.connect(dialog.reject)
		
		button_layout.addWidget(add_btn)
		button_layout.addWidget(cancel_btn)
		
		layout.addRow("", button_layout)
		dialog.setLayout(layout)
		dialog.exec()
	
	def add_category_dialog(self):
		"""Open a dialog to add a new category."""
		category_name, ok = QInputDialog.getText(
			self, "Add Category", "Enter new category name:"
		)
		
		if ok and category_name:
			if not category_name.strip():
				QMessageBox.warning(self, "Invalid Input", "Category name cannot be empty.")
				return
				
			if category_name in self.config:
				QMessageBox.critical(self, "Error", f"Category '{category_name}' already exists.")
				return
				
			# Add to config and create new tab
			self.config[category_name] = {}
			self.addCategoryTab(category_name)
			
			# Switch to the new tab
			self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
			
			self.statusBar.showMessage(f"Added category '{category_name}'", 3000)
			
			# If this is the first category, ask if they want to add a connection
			if len(self.config) == 1:
				reply = QMessageBox.question(
					self,
					"Add Connection",
					"Would you like to add your first SSH connection now?",
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
				)
				if reply == QMessageBox.StandardButton.Yes:
					self.add_connection_dialog()
	
	def deleteConnection(self, connection_name, category):
		"""Delete a connection from configuration and UI."""
		if connection_name not in self.config[category]:
			QMessageBox.critical(self, "Error", f"Connection '{connection_name}' not found.")
			return
		
		reply = QMessageBox.question(
			self, "Confirm Deletion",
			f"Are you sure you want to delete connection '{connection_name}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
		)
		
		if reply == QMessageBox.StandardButton.Yes:
			# Remove from config
			del self.config[category][connection_name]
			
			# Remove from list widget
			for i in range(self.connection_lists[category].count()):
				if self.connection_lists[category].item(i).text() == connection_name:
					self.connection_lists[category].takeItem(i)
					break
					
			self.statusBar.showMessage(f"Deleted connection '{connection_name}'", 3000)
			
			# If category is empty, ask if user wants to delete it
			if not self.config[category]:
				reply = QMessageBox.question(
					self, "Empty Category",
					f"Category '{category}' is now empty. Do you want to delete it?",
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
				)
				
				if reply == QMessageBox.StandardButton.Yes:
					# Remove category from config
					del self.config[category]
					
					# Remove tab
					for i in range(self.tab_widget.count()):
						if self.tab_widget.tabText(i) == category:
							self.tab_widget.removeTab(i)
							break
							
					# Remove from connection lists
					if category in self.connection_lists:
						del self.connection_lists[category]
						
					self.statusBar.showMessage(f"Deleted empty category '{category}'", 3000)
					
					# If no categories remain, prompt to create one
					if not self.config:
						self.promptFirstCategory()

	def save_config(self, config_file="config.json"):
		"""Save the current configuration to the JSON file."""
		try:
			# Create a backup first
			if os.path.exists(config_file):
				backup_file = f"{config_file}.bak.{int(time.time())}"
				with open(config_file, "r") as src, open(backup_file, "w") as dst:
					dst.write(src.read())
					
			with open(config_file, "w") as f:
				json.dump(self.config, f, indent=2)
				
			self.statusBar.showMessage(f"Configuration saved to {config_file}", 3000)
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
	
	def closeEvent(self, event):
		"""Override closeEvent to save configuration on exit."""
		reply = QMessageBox.question(
			self, "Confirm Exit",
			"Do you want to save changes before exiting?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
		)
		
		if reply == QMessageBox.StandardButton.Yes:
			self.save_config()
			event.accept()
		elif reply == QMessageBox.StandardButton.No:
			event.accept()
		else:
			event.ignore()

def load_config(config_file):
	"""Load the configuration JSON file."""
	try:
		with open(config_file, "r") as f:
			config = json.load(f)
			
		# Validate config structure
		if not isinstance(config, dict):
			raise ValueError("Configuration file must contain a dictionary")
			
		# Ensure all entries have the expected format
		for category, connections in config.items():
			if not isinstance(connections, dict):
				raise ValueError(f"Category '{category}' must contain a dictionary of connections")
				
			for name, settings in connections.items():
				if not isinstance(settings, dict) or "cmd" not in settings:
					raise ValueError(f"Connection '{name}' in category '{category}' must have a 'cmd' setting")
					
		return config
			
	except FileNotFoundError:
		return {}
	except json.JSONDecodeError:
		QMessageBox.critical(
			None, "Invalid Config", 
			"Configuration file is not a valid JSON. Using empty configuration."
		)
		return {}
	except ValueError as e:
		QMessageBox.critical(
			None, "Invalid Config Structure", 
			f"Configuration file has an invalid structure: {str(e)}. Using empty configuration."
		)
		return {}

def main():
	"""Main entry point for the application."""
	app = QApplication(sys.argv)
	
	# Set application icon
	app.setWindowIcon(QIcon.fromTheme("network-server"))
	
	config = load_config("config.json")
	main_window = SSHConnectionManager(config)
	main_window.show()
	sys.exit(app.exec())

if __name__ == "__main__":
	main()
