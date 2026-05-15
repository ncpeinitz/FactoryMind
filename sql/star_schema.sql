-- ==================================================

-- FactoryMind - Star Schema
-- Author: Nick Peinitz
-- Version: 1.0
-- Date: May 14, 2026

-- ===================================================

-- dim_Equipment
Create Table dim_Equipment (

	Equipment_Key	Int Primary Key Identity(1,1),
	Equipment_ID	Int	Not Null,
	Asset_Name		NVarchar(100)	Not Null,
	Asset_Tag		NVarchar(100)	Not Null,
	Location		NVarchar(100),
	Equipment_Type	NVarchar(100),
	Install_Date	Date

	);

-- dim_Technician
Create Table dim_Technician (

	Technician_Key	Int Primary Key Identity(1,1),
	Users_ID		Int	Not Null,
	Name			NVarchar(100)	Not Null,
	Skill_Level		NVarchar(50)

	);

-- dim_Date
Create Table dim_Date (

	Date_Key		Int Primary Key Identity(1,1),
	Full_Date		Date	Not Null,
	Day_of_Week		NVarchar(15)	Not Null,
	Week_Number		Int	Not Null,
	Month			Int	Not Null,
	Month_Name		NVarchar(15)	Not Null,
	Quarter			Int	Not Null,
	Year			Int	Not Null,
	Is_Weekend		Bit	Not Null

	);

-- fact_Work_Orders
Create Table fact_Work_Orders (

	Fact_ID				Int Primary Key Identity(1,1),
	Work_Order_ID		Int	Not Null,
	Equipment_Key		Int	Not Null,
	Technician_Key		Int	Not Null,
	Date_Key			Int Not Null,
	Parts_Cost			Decimal(10,2),
	Repair_Duration_Hrs	Decimal(6,2),
	Priority_Score		Int	Check(Priority_Score In (1, 2, 3, 4)),
	Is_Failure			Bit	Default 0,
	Constraint			FK_Fact_Work_Orders_Equipment	Foreign Key (Equipment_Key)	References dim_Equipment(Equipment_Key),
	Constraint			FK_Fact_Work_Orders_Technician	Foreign Key (Technician_Key)	References dim_Technician(Technician_Key),
	Constraint			FK_Fact_Work_Orders_Date	Foreign Key (Date_Key)	References dim_Date(Date_Key)

	);

-- ==========================
-- Indexes
-- ==========================

Create Index IX_Fact_Work_Orders_Equipment_Key On fact_Work_Orders(Equipment_Key);
Create Index IX_Fact_Work_Orders_Technician_Key On fact_Work_Orders(Technician_Key);
Create Index IX_Fact_Work_Orders_Date_Key On fact_Work_Orders(Date_Key);
Create Index IX_dim_Date_Year_Month On dim_Date(Year, Month);