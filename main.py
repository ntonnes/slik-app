'''
Created on Jun 28, 2022

@author: noaht
'''
#!/usr/bin/env python
import pathlib
import os
import math
from math import ceil
import tifffile as tf
import numpy as np
import tkinter as tk
from tkinter import filedialog as fd 
import tkinter.messagebox as tkmb



def reslice(file):
    #converts given array into a list (B,R,G) of arrays representing a reslice 
    #in the desired plane
    
    #initiate list to hold the resultant arrays
    resultList = []
    
    #reads the .tif file into an array of dimensions (Z,C,X,Y)
    arr = tf.imread(file)
    
    #reorient array to (Z,X,Y,C)
    arr = np.swapaxes(arr, 1,3)
    arr = np.swapaxes(arr, 1,2)
    
    #if plane choice is YZ, reorient array to (Y,Z,X,C)
    if app.planeChoice == 2:
        arr = np.swapaxes(arr, 0,2)
        arr = np.swapaxes(arr, 1,2)
        
    #if plane choice is XZ, reorient array to (X,Z,Y,C)
    if app.planeChoice == 3:
        arr = np.swapaxes(arr, 0,1)
        arr = np.flip(arr, 2)
        arr = np.flip(arr, 0)
        
    #call compress on the array
    arr = compress(arr)
    
    #call color transform on the compressed array and return a list of arrays
    resultList = colorTransform(arr, resultList)
    return resultList

def colorTransform(arr, resultList):
    #takes a compressed array and returns the colored arrays to be saved to .lsm files as a list
    
    #if greyscale, split arrays along the color axis and return them as a list
    if app.chromeChoice == 1:
        for stack in np.array_split(arr, 3, axis=3):
            resultList.append(np.squeeze(stack))
        return resultList
    
    #if color, create 4d arrays for each color and return as a list
    if app.chromeChoice == 2:
        template = np.array(np.zeros(arr.shape))
        red = np.stack((arr[:,:,:,1], template[:,:,:,0], template[:,:,:,0]), axis=3)       
        green = np.stack((template[:,:,:,0], arr[:,:,:,2], template[:,:,:,0]), axis=3)
        blue = np.stack((template[:,:,:,0], template[:,:,:,0], arr[:,:,:,0]), axis=3)
        resultList.append(blue)
        resultList.append(red)
        resultList.append(green)
        return resultList
    
    #if composite, return one rolled 4d array
    if app.chromeChoice == 3:
        arr = np.roll(arr, 2, axis=3)
        resultList.append(arr)
        return resultList
                        
def compress(arr):
    #compresses the given array along the current axis to the degree specified 
    #in the spinbox
    
    #retrieves the requested compression factor  
    compression = int(app.slices.get())
    
    #return if there is no compression
    if compression == 1:
        return arr
    
    #create a new array with the dimensions of the input array after compression
    Zframes = ceil((arr.shape)[0] / compression)
    arrCompressed = np.zeros((Zframes, (arr.shape)[1], (arr.shape)[2], (arr.shape)[3]))
    
    #initialize some counters
    frame = 0
    count = 1
    
    #iterate through the empty Zframes of the empty array
    while count <= Zframes:
        
        #if the number of remaining frames is less than the compression factor, set tmp to the remaining frames
        if (compression*count-1 > (arr.shape)[0]):
            tmp = arr[frame:,:,:,:]
            
        #if the number of remaining frames is greater than the compression factor, set tmp to the number of 
        #frames specified by the compression factor
        else:
            tmp = arr[frame:(compression*count-1),:,:,:]
            
        #compress the selected frames based on the compression style choice
        if app.styleChoice==1:
            frameCondensed = np.maximum.reduce(tmp, axis=0)
        if app.styleChoice==2:
            frameCondensed = np.minimum.reduce(tmp, axis=0)
        if app.styleChoice==3:
            frameCondensed = np.add.reduce(tmp, axis=0) 
            
        #add the compressed frame to the empty array       
        arrCompressed[(count-1),:,:,:] = frameCondensed
        
        #advance counters
        frame = frame + compression
        count = count + 1
        
    #return the compressed array
    return arrCompressed

def save(fileList):
    #calls reslice and saves the return as .tif files in appropriate locations
    
    #initiate some variables
    reslicedList = []
    modes = ['[B]','[R]','[G]']
    file = 0
    
    #iterate through the list of files retrieved in main
    for LSM in fileList:
        
        #get the directory location of the current file
        directory = app.dirList[file]
        
        #call reslice on that file's directory
        reslicedList.append(reslice(directory))
        
        #reset mode to 0
        mode = 0
        
        #create a folder for the outputs of the current file
        tmp = directory.split('.lsm')[0] 
        folderPath = addFolder(tmp)
        
        #iterate through the list of arrays returned by the reslice call on current file       
        for arr in reslicedList[file]:
            
            #set the name variable of the current array (mode included if list>1)
            if len(reslicedList[file])== 1:
                name = LSM.split('.lsm')[0] + '[RGB].tif'
            else:
                name = LSM.split('.lsm')[0] + modes[mode] + '.tif'
                mode = mode+1
            path = os.path.join(folderPath, name)
            
            #if chrome choice is color, add metadata and write
            if app.chromeChoice != 1:
                tf.imwrite(path, arr.astype('uint8'), dtype='uint32', photometric='rgb')
                
            #if chrome choice is greyscale, write as is
            if app.chromeChoice == 1:
                tf.imwrite(path, arr.astype('uint8'))
            
        #advance file number
        file = file+1
   
    
def addFolder(name):
    #adds a folder with the given name to the root directory
    curDir = pathlib.Path().resolve()
    finalDir = os.path.join(curDir, name)
    if not os.path.exists(finalDir):
        os.makedirs(finalDir)
    return finalDir
    
def main():
    #executes with the helper methods above; returns R,G,B .tif files in folders in the same directory as the .lsm file
    
    #if a slicing plane was not selected: try again
    if app.planeChoice == 0:
        tkmb.showerror('ERROR', 'Please choose a slicing plane')
        return
    
    #if a condensation style was not selected: try again
    if app.styleChoice == 0:
        tkmb.showerror('ERROR', 'Please choose a condensation style')
        return
    #if a color style was not selected: try again
    if app.chromeChoice == 0:
        tkmb.showerror('ERROR', 'Please choose a color style')
        return
    
    #retrieve a list of all given files
    fileList = app.Listbox.get(0, tk.END)
    
    #initiate processing by calling save
    save(fileList)

class Application(tk.Frame):
    #initializes the frame from which he application runs
    
    #creates the initial window upon launch
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)   
        self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
        self.createWidgets()
        self.planeChoice=0
        self.styleChoice=0
        self.chromeChoice=0
        self.dirList=[]
        
    #populates the application window
    def createWidgets(self):
        
        #configures the grid in which the widgets will sit
        top=self.winfo_toplevel()                
        top.rowconfigure(0, weight=1)            
        top.columnconfigure(0, weight=1)         
        self.rowconfigure(0, weight=1)           
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1) 
        self.columnconfigure(1, weight=1)          
        self.columnconfigure(2, weight=1)      
        
        #CHOOSE FILE: opens window explorer for file selection, calls openFile
        self.Button = tk.Button(self, text='Choose Experimental Confocals (.lsm)', command=openFile)
        self.Button.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W, padx=10, pady=10)
        
        #SCROLLBAR: scrolls through selected files
        self.xScroll = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.xScroll.grid(row=2, column=0, sticky=tk.E+tk.W)
        
        #LISTBOX: shows selected files
        self.Listbox = tk.Listbox(self, height = 5, xscrollcommand=self.xScroll.set, width=50, selectmode=tk.MULTIPLE)
        self.Listbox.grid(row=1, column=0, rowspan=1)
        self.xScroll['command'] = self.Listbox.xview
        
        #GO: calls the main method
        self.Button = tk.Button(self, text='Go', command=main, width=5, height=1, bd=4)
        self.Button.grid(row=1, column=1, sticky=tk.W+tk.S, pady=10)
        
        #DELETE: removes a selected file, calls delete
        self.Button = tk.Button(self, text='Delete', command=delete, width=5, height=1, bd=4)
        self.Button.grid(row=1, column=1, sticky=tk.W+tk.S, padx=60, pady=10)          
        
        #PLANE: selection for slicing plane
        entries = ['XY', 'YZ', 'XZ']
        plane = tk.StringVar()
        plane.set('select plane')
        self.Plane = tk.OptionMenu(self, plane, *entries, command=planeSelect)
        self.Plane.grid(row=0, column=1, sticky=tk.N, pady=15)
        
        #CONDENSATION: selection for pixel brightness after condensation
        entries = ['maximum', 'minimum', 'composite']
        style = tk.StringVar()
        style.set('condensation style')
        self.Style = tk.OptionMenu(self, style, *entries, command=styleSelect)
        self.Style.grid(row=0, column=1, sticky=tk.S, pady=35) 
        
        #COLOR: color style selection for the saved lsm files
        entries = ['greyscale', 'color', 'composite']
        color = tk.StringVar()
        color.set('color style')
        self.Color = tk.OptionMenu(self, color, *entries, command=chromeSelect)
        self.Color.grid(row=0, column=1, sticky=tk.N, pady=50)               
 
        #SPINBOX LABEL: label for the spinbox widget
        self.labelslices = tk.LabelFrame(self, text='condensation factor', labelanchor='n', width=125, height=50)
        self.labelslices.grid(row=1, column=1, sticky=tk.N) 
        
        #SPINBOX: selection for frames per condensed frame
        self.slices = tk.Spinbox(self, increment=1, width=10, from_=1, to=math.inf)
        self.slices.grid(row=1, column=1, sticky=tk.N, pady=20)

    
#callback function for selecting files to be manipulated; only accepts lsm files
def openFile():    
    directory = fd.askopenfilename() 
    file = os.path.basename(os.path.normpath(directory))
    if file!='.':
        if '.lsm' not in file:
            tkmb.showerror('ERROR', 'Selected files must be in .lsm format')
        if file in app.Listbox.get(0, tk.END):
            tkmb.showerror('ERROR', 'File already selected')
        else:
            app.Listbox.insert(tk.END, file)
    app.dirList.append(directory)
    
#helper methods to the option widgets                              
def planeSelect(plane):
    if plane == 'XY':
        app.planeChoice=1
    if plane == 'YZ':
        app.planeChoice=2
    if plane == 'XZ':
        app.planeChoice=3

def styleSelect(style):
    if style == 'maximum':
        app.styleChoice=1
    if style == 'minimum':
        app.styleChoice=2
    if style == 'composite':
        app.styleChoice=3 

def chromeSelect(chrome):
    if chrome == 'greyscale':
        app.chromeChoice=1
    if chrome == 'color':
        app.chromeChoice=2
    if chrome == 'composite':
        app.chromeChoice=3

#helper method to the listbox menu; deletes entries        
def delete():
    selectedTup = app.Listbox.curselection()
    descending = sorted(selectedTup, reverse=True)
    for line in descending:
        app.Listbox.delete(line)
        del app.dirList[line]
        

#configurations for the application frame
app = Application()
app.master.geometry('500x300')
app.master.title('396 Application')
app.mainloop()   
