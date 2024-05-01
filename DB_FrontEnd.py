# import dependencies
import tkinter
import tkinter.messagebox
import customtkinter
import sqlite3

#design page
customtkinter.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

#Frame's class definition
class MyFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # add widgets onto the frame...
        self.text_var = tkinter.StringVar(value="") # to remove label name
        self.label = customtkinter.CTkLabel(self, textvariable= self.text_var)
        self.label.grid(row=1, column=1, padx=20)
        
        

#Front end application
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # Setting branch id in app for each branch [change if app is running in different branch locaation]
        self.branch = 50504

        # configure window
        self.title("Retailer Page")
        self.geometry(f"{1200}x{700}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=100) #here here
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        #add side bar buttons
        self.sidebar_frame = customtkinter.CTkFrame(self, width=50, corner_radius=10)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure((0,1,2,3,4,5), weight=0)
        self.sidebar_frame.grid_rowconfigure(6, weight=3)
        self.sidebar_frame.grid_rowconfigure((7,8,9,10), weight=0)

        self.my_frame = MyFrame(master=self)
        self.my_frame.grid(row=0, column=1, padx=20, pady=20, sticky="new")

        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, command=self.UpdateDB, text="New stock Arrival")
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        
        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, command=self.CheckDB, text="Check Database")
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = customtkinter.CTkButton(self.sidebar_frame, command=self.SearchDB, text="Search Product")
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar_button_4 = customtkinter.CTkButton(self.sidebar_frame, command=self.DBRestockQuery, text="Restock")
        self.sidebar_button_4.grid(row=4, column=0, padx=20, pady=10)

        self.sidebar_button_5 = customtkinter.CTkButton(self.sidebar_frame, command=self.RestockDetails, text="Requested Products")
        self.sidebar_button_5.grid(row=5, column=0, padx=20, pady=10)

        # customizable front-end design
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["System", "Dark", "Light"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 10))

        # customizable front-end design
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=9, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"], command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20))



    # sidebar button functions - gui interface functions
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)



    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)



    #sidebar button functions
    def UpdateDB(self):
        self.clear_frame()
        self.controller_button = customtkinter.CTkButton(self.my_frame, command=self.getdetails_UpdateDB, text="New Entry")
        self.controller_button.grid(row=0, column=1, padx=20, pady=20)



    def CheckDB(self):
        self.clear_frame()
        self.streaming_button = customtkinter.CTkButton(self.my_frame, command=self.viewtable, text="Check Database")
        self.streaming_button.grid(row=0, column=1, padx=20, pady=20)



    def SearchDB(self):
        self.clear_frame()
        self.communication_button = customtkinter.CTkButton(self.my_frame, command=self.getdetails_SearchDB, text="Search New Entry")
        self.communication_button.grid(row=0, column=1, padx=20, pady=20)



    def DBRestockQuery(self):
        self.clear_frame()
        self.visualizer_button = customtkinter.CTkButton(self.my_frame, command=self.getdetails_RestockDB, text="Restock Query")
        self.visualizer_button.grid(row=0, column=1, padx=20, pady=20)



    def clear_frame(self):
        for widget in self.my_frame.winfo_children():
            widget.destroy()


    # TEMPORARY FUNCTION
    #def dummy_func(self):
    #    print("YET TO BE UPDATED")
    


    # main frame button functions
    def getdetails_UpdateDB(self):
        # product name input
        self.text_var = tkinter.StringVar(value="Product Name :")
        self.label_name = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        self.label_name.grid(row=1, column=1)
        self.entry_name = customtkinter.CTkEntry(self.my_frame, placeholder_text='Enter Product Name ', width=400)
        self.entry_name.grid(row=1, column=2)

        # new quantity input
        self.text_var = tkinter.StringVar(value="Quantity Arrived :")
        self.label_qty = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        self.label_qty.grid(row=2, column=1)
        self.entry_qty = customtkinter.CTkEntry(self.my_frame, placeholder_text='Enter Quantity Arrived ', width=400)
        self.entry_qty.grid(row=2, column=2)

        # get the input data
        retreival_button1 = customtkinter.CTkButton(self.my_frame, command=self.retreive_UpdateDB, text="Update Database")
        retreival_button1.grid(row=3, column=1, padx=20, pady=20)



    def retreive_UpdateDB(self):
        self.pname = self.entry_name.get()
        self.pqty = self.entry_qty.get()
        self.pqty = int(self.pqty)
        #print(type(self.pname), type(self.pqty))

        self.updatetable(self.pname,self.pqty)


#CODE FROM HERE
    def updatetable(self,prod_name, prod_qty):
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        self.removerequest(prod_name, prod_qty)

        sql = "SELECT Quantity FROM Product_Details WHERE ProductName = ?"
        r_set = conn.execute(sql, [prod_name])

        for val in r_set:
            old_value = val
        
        new_value = old_value[0] + prod_qty
        #print(old_value[0])
        #print(new_value)

        sql = "UPDATE Product_Details SET Quantity = ? WHERE ProductName = ?"
        conn.execute(sql, [new_value, prod_name])

        conn.commit()

        #HERE
        text = "Update {} --> old-value : {}    new-value: {}".format(self.pname, old_value[0], new_value)
        self.text_var = tkinter.StringVar(value=text)
        label_confirmation = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        label_confirmation.grid(row=4, column=2)

        conn.close()



    def viewtable(self):
            column_name = ['Product ID', 'Product Name', 'Product Cost', 'Quantity']

            conn = sqlite3.connect('./BackEnd/RetailerDB')

            r_set=conn.execute('SELECT * from Product_Details')

            for i in range (4):
                e = customtkinter.CTkLabel(self.my_frame, width=50, text=column_name[i], anchor='w')
                e.grid(row=1, column=i,padx=20)
            i=0 # row value inside the loop 
            for row in r_set: 
                for j in range(len(row)):
                    e = customtkinter.CTkLabel(self.my_frame, width=50,text=row[j],anchor='w') 
                    e.grid(row=i+2, column=j,padx=20) 
                i=i+1

            conn.close()



    def getdetails_SearchDB(self):
        self.text_var = tkinter.StringVar(value="Product Name :")
        self.label_name = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        self.label_name.grid(row=1, column=1)
        self.entry_name = customtkinter.CTkEntry(self.my_frame, placeholder_text='partial / whole word', width=400)
        self.entry_name.grid(row=1, column=2)

        retreival_button2 = customtkinter.CTkButton(self.my_frame, command=self.retreive_SearchDB, text="Search Table")
        retreival_button2.grid(row=2, column=1, padx=20, pady=20)



    def retreive_SearchDB(self):
        self.pname = self.entry_name.get()
        self.searchprod(self.pname)



    def searchprod(self, prod_name):
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        column_name = ['Product ID', 'Product Name', 'Product Cost', 'Quantity']

        sql = " SELECT * FROM Product_Details WHERE productname like ?"
        r_set = conn.execute(sql, ['%' + prod_name + '%'])

        self.clear_frame()

        self.getdetails_SearchDB()

        for i in range (4):
            e = customtkinter.CTkLabel(self.my_frame, width=50, text=column_name[i], anchor='w')
            e.grid(row=3, column=i,padx=20)
        i=4 # row value inside the loop 
        for row in r_set: 
            for j in range(len(row)):
                e = customtkinter.CTkLabel(self.my_frame, width=50,text=row[j],anchor='w') 
                e.grid(row=i, column=j,padx=20) 
            i=i+1

        conn.close()



    def getdetails_RestockDB(self):
        self.text_var = tkinter.StringVar(value="Quantity Lower Limit")
        self.label_name = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        self.label_name.grid(row=1, column=1)
        self.entry_name = customtkinter.CTkEntry(self.my_frame, placeholder_text='Quantity below which products need to be displayed', width=400)
        self.entry_name.grid(row=1, column=2)
    
        retreival_button3 = customtkinter.CTkButton(self.my_frame, command=self.retreive_RestockDB, text="Check stock")
        retreival_button3.grid(row=2, column=1, padx=20, pady=20)



    def retreive_RestockDB(self):
        self.qty = self.entry_name.get()
        self.searchstock(self.qty)



    def searchstock(self, prod_qty):
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        column_name = ['Product ID', 'Product Name', 'Product Cost', 'Quantity']

        sql = " SELECT * FROM Product_Details WHERE Quantity < ?"
        r_set = conn.execute(sql, [prod_qty])

        self.clear_frame()

        self.getdetails_RestockDB()

        for i in range (4):
            e = customtkinter.CTkLabel(self.my_frame, width=50, text=column_name[i], anchor='w')
            e.grid(row=3, column=i,padx=20)
        i=4 # row value inside the loop 
        for row in r_set: 
            for j in range(len(row)):
                e = customtkinter.CTkLabel(self.my_frame, width=50,text=row[j],anchor='w') 
                e.grid(row=i, column=j,padx=20) 
            i=i+1

        self.index = i+1

        retreival_button5 = customtkinter.CTkButton(self.my_frame, command=self.getdetails_Restock, text="Order Restock")
        retreival_button5.grid(row=i+1, column=1, padx=20, pady=20)



    def getdetails_Restock(self):
        self.text_var = tkinter.StringVar(value="Product ID's : ")
        self.label_name = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        self.label_name.grid(row=self.index+1, column=1)    
        self.entry_name = customtkinter.CTkEntry(self.my_frame, placeholder_text="ProdID1-qty1 ProdID2-qty2 ProdID3-qty3 ...(space btw each prodID-qty)", width=400)
        self.entry_name.grid(row=self.index+1, column=2)
    
        retreival_button4 = customtkinter.CTkButton(self.my_frame, command=self.retreive_OrderDetails, text="Create Request")
        retreival_button4.grid(row=self.index+2, column=1, padx=20, pady=20)



    def retreive_OrderDetails(self):
        #self.getdetails_Restock()
        details = self.entry_name.get()
        details = details.split(" ")
        #print(details)

        self.Order(details)


    #CHECKKKKKKKK
    def Order(self, prod):
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        sql = "insert into Branch_Request (ProductID, BranchID, RequestedQty) values(?,?,?)"

        for index in range(0, len(prod), 2):
            print(index)
            print(prod[index])
            print(prod[index+1])
            r_set = conn.execute(sql, [prod[index], self.branch, int(prod[index+1])])
        
        text = "Order Sent"
        self.text_var = tkinter.StringVar(value=text)
        label_confirmation = customtkinter.CTkLabel(self.my_frame, textvariable= self.text_var)
        label_confirmation.grid(row=index+2, column=2)

        conn.commit()

        conn.close()



    def RestockDetails(self):
        self.clear_frame()
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        column_name = ['Product ID', 'Branch ID', "Requested Quantity"]

        sql = "select * from Branch_Request"
        r_set = conn.execute(sql)

        for i in range (3):
            e = customtkinter.CTkLabel(self.my_frame, width=50, text=column_name[i], anchor='w')
            e.grid(row=1, column=i,padx=20)
        i=2 # row value inside the loop 
        for row in r_set: 
            for j in range(len(row)):
                e = customtkinter.CTkLabel(self.my_frame, width=50,text=row[j],anchor='w') 
                e.grid(row=i, column=j,padx=20)
            i=i+1

        conn.close()



    def removerequest(self,name, qty):
        conn = sqlite3.connect('./BackEnd/RetailerDB')

        sql = "select ProductID from Product_Details where ProductName = ?"
        r_set = conn.execute(sql, [name])
        for row in r_set:
            prodid = row[0]

        sql = "select RequestedQty from Branch_Request where ProductID = ?"
        r_set = conn.execute(sql, [prodid])
        for row in r_set:
            requestedqty = row[0]
        
        required = requestedqty - qty

        if(required <= 0):
            sql = "delete from Branch_Request where ProductID = ?"
            r_set = conn.execute(sql, [prodid])
        else:
            sql = "update Branch_Request set RequestedQty = ? where ProductID = ?"
            r_set = conn.execute(sql, [required, prodid])

        conn.commit()

        conn.close()
        
        


if __name__ == "__main__":
    app = App()
    app.mainloop()