from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
import os
from selenium import webdriver
import clipboard    #for pasting copied instance
from bs4 import BeautifulSoup


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#path of uploaded file
path = "a"
savedFormPath = "a"
data = ""
webdriverPath = os.path.join(BASE_DIR,'chromedriver')

def home(request):
	return render(request, 'home.html')


def py_upload(request):

    if request.method == 'POST':
        uploaded_file = request.FILES.get('document',False)
        if(uploaded_file): #if file is selected
            fs = FileSystemStorage()
            name = fs.save(uploaded_file.name, uploaded_file)
            global path
            path = fs.path(name)
            #debug print("THE PATH ",path)

            global webdriverPath
            driver = webdriver.Chrome(executable_path = webdriverPath)
            driver.get("https://server001.cloudehrserver.com/cot/opt/html_form_generator")

            fileinput = driver.find_element_by_id("validatedCustomFile")
            #get path of opt from system
            #global path
            fileinput.send_keys(path)

            submitbutton = driver.find_element_by_name("doit")
            submitbutton.click()
            element = driver.find_element_by_xpath("/html/body/main/section/div/section/div")
            source_code = element.get_attribute("outerHTML")
            driver.quit()

            #source code with archetype slot errors. Remove this and send new source code
            soup = BeautifulSoup(source_code, 'html.parser')
            #change heading
            headingElement = soup.find_all('h2')
            if( len(headingElement) == 1 ):
                headingElement[0].decompose()


            #Remove archetype slot
            labelElements = soup.find_all('label')
            for label in labelElements:
                if "ARCHETYPE_SLOT" in label.text:
                    label.decompose()
                if (label.text=="Event Series" or label.text=="Any event" or label.text=="Tree" or label.text=="List" or label.text=="structure" or label.text=="history"):  #extra stuff to be removed from form
                    label.decompose()

            # making the observations bold
            divs = soup.find_all('div', {'class':"OBSERVATION"})
            for div in divs:
            	temp = div.label
            	new_tag = soup.new_tag('b')
            	strs = temp.text
            	temp.clear()
            	temp.insert(1, new_tag)
            	temp.b.append(strs)

            global data
            data = str(soup)

            #delete file from django(local)
            fs.delete(name)

            ##create new html file
            newfilepath = os.path.join(BASE_DIR,'templates')
            newfilepath = os.path.join(newfilepath,'form.html')
            newfileobject = open(newfilepath,"w+")

            #add button code to html
            htmlheadString ="""<!DOCTYPE html>
            <html>
                <head>
                    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
                    <title>Form</title>
                </head>
                <body>
            <form action="" method="post">
                {% csrf_token %}
            """

            buttonString = """<div class="container">
            <input type="submit" name="Submit" value="Submit" />
            </div>
            </form>
            </html>
            """

            data = htmlheadString + data + "\n" + buttonString
            newfileobject.write(data)
            newfileobject.close()

            return redirect ('/form/')
            ##
            ##

    return render(request,'upload.html')


def py_form(request):

    import ast
    from bs4 import BeautifulSoup

    if request.method == 'POST':
        ##TODO submit and send true false whether successful or not
        temp = str(request.POST)
        POSTdata = ""
        flag = 0
        for char in temp :
            if(char == '{'):
                flag = 1
            if(flag == 1):
                POSTdata = POSTdata + char
            if(char == '}'):
                flag = 0
                break

        rules = ast.literal_eval(POSTdata) # it is now a python dictionary

        #opening form file
        form = os.path.join(BASE_DIR,'templates')
        form = os.path.join(form,'form.html')
        formObject = open(form,"r")
        data = formObject.read()
        formObject.close()

        #editing form with POST values
        sourceCode = data
        soup = BeautifulSoup(sourceCode, 'html.parser')

        for key, value in rules.items():
            value = value[0]
            #searching for 'input' tag
            try:
                soup.find('input', {'name' : key})['value'] = value
            except TypeError:
                pass

            #searching for 'select' tag
            selects = soup.find('select', {'name' : key})
            try:
                children = selects.findChildren('option', {'value':value})
                for child in children:
                    child['selected'] = "selected"
            except AttributeError:
                pass

        # saving modified data in a different file
        savedForm = os.path.join(BASE_DIR,'templates')
        savedForm = os.path.join(savedForm,'savedForm.html')
        global savedFormPath
        savedFormPath = savedForm  #used in validating
        savedFormObject = open(savedForm,"w+")
        savedFormObject.write(str(soup))
        savedFormObject.close()
        #debug print("SECOND PATH ", savedForm)

        return redirect('/response/')

    return render(request,'form.html')    

def py_response(request):
    if request.method == 'POST':
        global webdriverPath
        driver = webdriver.Chrome(executable_path = webdriverPath)
        driver.get("https://server001.cloudehrserver.com/cot/opt/xml_instance_validator")

        fileinput = driver.find_element_by_id("validatedCustomFile")
        #get path of opt from system
        #global path
        fileinput.send_keys(savedFormPath)
        submitbutton = driver.find_element_by_name("doit")
        submitbutton.click()
        element = driver.find_element_by_xpath("/html/body/main/section[2]/div")
        source_code = element.get_attribute("outerHTML")
        driver.quit()
        #remove heart element
        soup = BeautifulSoup(source_code,'html.parser')
        heartElement = soup.find("svg",{'class':"heart"})
        if heartElement:
            heartElement.decompose()
        resultTag  = soup.find("h2")
        if "is valid" in resultTag.text:
            resultTag.string.replace_with("Document instance is valid!")
        htmlheadString ="""<!DOCTYPE html>
            <html>
                <head>
                    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
                    <title>Validator Response</title>
                </head>
                <body>
            <form action="" method="post">
                {% csrf_token %}
            """

        buttonString = """<div class="container">
            <form action="" method="post">
                    {% csrf_token %}
                    <input type="submit" name="valid" value="Upload Again" />
                    
                </form>
            </div>
        """
        source_code = htmlheadString + "\n"+ str(soup) + "\n"+ buttonString
        newfilepath = os.path.join(BASE_DIR,'templates')
        newfilepath = os.path.join(newfilepath,'valid.html')
        newfileobject = open(newfilepath,"w+")
        newfileobject.write(source_code)
        newfileobject.close()
        return redirect('/valid/')


    return render(request,'response.html')

def py_valid(request):
    if request.method == 'POST':
        return redirect('/upload/')
    return render(request,'valid.html') 


