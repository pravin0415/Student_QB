
from email.mime import image
from tkinter import*
from tkinter import messagebox
import pymysql
import qrcode
from PIL import Image, ImageTk
from resizeimage import resizeimage

class Qr_Generator:
    def __init__(self, root):
        self.root = root
        self.root.geometry("900x500+200+50")
        self.root.title("QR Generator | Developed By Lalit & Group Members")
        self.root.resizable(False, False)

        title = Label(self.root, text="Student Attendance System", font=(
            "times new roman", 40), bg='#053246',fg="white").place(x=0, y=0, relwidth=1)

        self.var_student_Id = StringVar()
        self.var_student_name = StringVar()
        self.var_student_Department = StringVar()
        self.var_student_class = StringVar()
        self.var_student_Phone = StringVar()
        self.var_alternate_Phone = StringVar()

        student_Frame = Frame(self.root, bd=2, relief=RIDGE, bg='white')
        student_Frame.place(x=50, y=90, width=500, height=400)
        student_title = Label(student_Frame, text="Student Details", font=(
            "goudy old style", 30), bg='#043256', fg='white').place(x=0, y=0, relwidth=1)

        lb_student_Id = Label(student_Frame, text="Student ID", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=63)
        lb_student_Name = Label(student_Frame, text="Name", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=103)
        lb_student_department = Label(student_Frame, text="Department", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=143)
        lb_student_class = Label(student_Frame, text="Class", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=183)
        lb_student_phone = Label(student_Frame, text="Phone_No", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=223)
        lb_alternate_phone = Label(student_Frame, text="Alternate_No", font=(
            "times new roman", 15, 'bold'), bg='white').place(x=20, y=262)

        txt_student_Id = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_student_Id, bg='lightyellow').place(x=200, y=62)
        txt_student_Name = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_student_name, bg='lightyellow').place(x=200, y=102)
        txt_student_department = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_student_Department, bg='lightyellow').place(x=200, y=142)
        txt_student_class = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_student_class, bg='lightyellow').place(x=200, y=182)
        txt_student_phone = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_student_Phone, bg='lightyellow').place(x=200, y=222)
        txt_alternate_phone = Entry(student_Frame, text="", font=(
            "times new roman", 15), textvariable=self.var_alternate_Phone, bg='lightyellow').place(x=200, y=262)


        btn_generate = Button(student_Frame, text='QR Generate', command=self.genrate, font=(
            "times new roman", 18, 'bold'), bg='#2196f3', fg='white').place(x=90, y=300, width=180, height=30)
        btn_clear = Button(student_Frame, text='Clear', command=self.clear, font=(
            "times new roman", 18, 'bold'), bg='#607d8b', fg='white').place(x=290, y=300, width=120, height=30)

        self.msg = ''
        self.lbl_msg = Label(student_Frame, text=self.msg, font=(
            "times new roman", 20), bg='white', fg='green')
        self.lbl_msg.place(x=0, y=340, relwidth=1)

        QR_Frame = Frame(self.root, bd=2, relief=RIDGE, bg='white')
        QR_Frame.place(x=600, y=90, width=250, height=400)
        student_title = Label(QR_Frame, text="Student QR Code", font=(
            "goudy old style", 20), bg='#043256', fg='white').place(x=0, y=0, relwidth=1)

        self.QR_code = Label(QR_Frame, text='QR Code\nNot Available', font=(
            'times new roman', 15), bg='#3f51b5', fg='white')
        self.QR_code.place(x=35, y=120, width=180, height=180)

    def clear(self):
        self.var_student_Id.set('') 
        self.var_student_name.set('')
        self.var_student_Department.set('')
        self.var_student_class.set('')
        self.var_student_Phone.set('')
        self.var_alternate_Phone.set('')
        self.msg=''
        self.lbl_msg.config(text=self.msg)
        self.qr_code.config(image='')
        
    def genrate(self):
        if (self.var_student_class.get() == '' or self.var_student_Id.get() == '' or self.var_student_Department.get() == '' or self.var_student_name.get() == ''or self.var_student_Phone.get() ==''or self.var_alternate_Phone.get() == ''):
            self.msg = 'ALL Fields are Required!!!'
            self.lbl_msg.config(text=self.msg, fg='red')
        elif((self.var_student_Id.get().isdigit())!=True):
            self.msg= 'Please Enter Valid Details !!!'
            self.lbl_msg.config(text=self.msg, fg='red')
        else:
            qr_data = f"Student ID: {self.var_student_Id.get()}\nStudent Name:{self.var_student_name.get()}\nDepartment: {self.var_student_Department.get()}\nClass:{self.var_student_class.get()}\nPhone_No:{self.var_student_Phone.get()}\nAlternate_No:{self.var_alternate_Phone.get()}"
            QR_code = qrcode.make(qr_data)
            QR_code=resizeimage.resize_cover(QR_code,[180, 180])
            QR_code.save("Student_QR/std_"+str(self.var_student_Id.get())+'.png')
            self.im = ImageTk.PhotoImage(file="Student_QR/std_"+str(self.var_student_Id.get())+'.png')
            self.QR_code.config(image=self.im)
            self.msg = 'QR Generated Successfully!!'
            self.lbl_msg.config(text=self.msg, fg='green')
        try:
            con = pymysql.connect(host="localhost", user="root", password="Lalit@2002", database="student_db")
            cur = con.cursor()

            cur.execute("INSERT INTO student_db(rollNo, name, department, class, Phone_No, Alternate_No) VALUES(%s, %s, %s, %s, %s, %s)",
                    (
                    self.var_student_Id.get(),
                    self.var_student_name.get(),
                    self.var_student_Department.get(),
                    self.var_student_class.get(),
                    self.var_student_Phone.get(),
                    self.var_alternate_Phone.get()
                    
            
            ))
            con.commit()
            con.close()
            messagebox.showinfo("Success", "Register successful")


        except Exception as es:
            self.QR_code.config(image=self.im)
            self.msg = 'QR Already present !!'
            self.lbl_msg.config(text=self.msg, fg='red')
            messagebox.showerror("error", "The data already precent")
            
            

root = Tk()
obj = Qr_Generator(root)
root.mainloop()
