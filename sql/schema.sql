-- ==================================================

-- FactoryMind - OLTP Schema
-- Author: Nick Peinitz
-- Version: 1.0
-- Date: May 9, 2026

-- ===================================================

-- Users
Create Table Users (

	Users_ID	Int Primary Key Identity(1,1),
	Name		NVarchar(100) Not Null,
	Email		NVarchar(150) Not Null Unique,
	Role		NVarchar(50) Not Null Check (Role in ('Operator', 'Technician', 'Supervisor')),
	Created_At	DateTime2	Default GetDate()

	);

-- Equipment
Create Table Equipment (

	Equipment_ID	Int Primary Key Identity(1,1),
	Asset_Name		NVarchar(100) Not Null,
	Asset_Tag		NVarchar(50) Not Null Unique,
	Location		NVarchar(100),
	Status			NVarchar(50) Check (Status in ('Operational', 'Under Repair', 'Decommissioned')),
	Install_Date	Date,
	Blob_URL		NVarchar(500),
	Created_At		DateTime2	Default GetDate()

	);

-- Work_Orders
Create Table Work_Orders (

	Work_Order_ID		Int Primary Key Identity(1,1),
	Equipment_ID		Int Not Null,
	Assigned_Tech_ID	Int,
	Reported_By_ID		Int,
	Failure_Type		NVarchar(100),
	Priority			NVarchar(20)	Check (Priority in ('Low', 'Medium', 'High', 'Critical')),
	Status				NVarchar(40)	Check (Status in ('Open', 'In Progress', 'Completed', 'Cancelled')),
	Notes				NVarchar(Max),
	Parts_Cost			Decimal(10,2),
	Repair_Duration_Hrs	Decimal(5,2),
	Created_At			DateTime2	Default GetDate(),
	Completed_At		DateTime2,
	Constraint FK_Work_Orders_Equipment		Foreign Key (Equipment_ID)	References Equipment(Equipment_ID),
	Constraint FK_Work_Orders_Technician	Foreign Key (Assigned_Tech_ID)	References Users(Users_ID),
	Constraint FK_Work_Orders_Reporter		Foreign Key (Reported_By_ID)	References Users(Users_ID)

	);

-- Parts_Usage
Create Table Parts_Usage (

	Part_ID			Int Primary Key Identity(1,1),
	Work_Order_ID	Int Not Null,
	Part_Name		NVarchar(150) Not Null,
	Quantity_Used	Int		Not Null Default 1,
	Unit_Cost		Decimal(10,2),
	Recorded_At		DateTime2	Default GetDate(),
	Constraint FK_Parts_Usage_Work_Order Foreign Key (Work_Order_ID) References Work_Orders(Work_Order_ID)

	);

-- Sensor_Events
Create Table Sensor_Events (

	Event_ID		Int Primary Key Identity(1,1),
	Equipment_ID	Int Not Null,
	Temperature_C	Decimal(5,2),
	Vibration_Hz	Decimal(6,2),
	Torque_Nm		Decimal(6,2),
	Rotational_RPM	Int,
	Tool_Wear_Min	Int,
	Is_Anomaly		Bit		Default 0,
	Recorded_At		DateTime2	Default GetDate(),
	Constraint FK_Sensor_Events_Equipment	Foreign Key (Equipment_ID)	References Equipment(Equipment_ID)

	);

-- Query_Logs
Create Table Query_Logs (

	Log_ID		Int Primary Key Identity(1,1),
	Users_ID	Int,
	Query_Text	NVarchar(1000),
	Logged_At	DateTime2 Default GetDate(),
	Response_Ms	Int,
	Constraint FK_Query_Logs_User	Foreign Key (Users_ID)	References Users(Users_ID)

	);

-- ==========================
-- Indexes
-- ==========================

Create Index IX_Work_Orders_Equipment_ID On Work_Orders(Equipment_ID);
Create Index IX_Work_Orders_Created_At On Work_Orders(Created_At);
Create Index IX_Work_Orders_Status On Work_Orders(Status);
Create Index IX_Work_Orders_Composite On Work_Orders(Equipment_ID, Status, Created_At);
Create Index IX_Sensor_Events_Equipment_ID On Sensor_Events(Equipment_ID);
Create Index IX_Sensor_Events_Recorded_At On Sensor_Events(Recorded_At);
Create Index IX_Query_Logs_Timestamp On Query_Logs(Logged_At);
