from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#path of uploaded file
path = "a"
data = ""

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
            
            ##
            ##
            from selenium import webdriver
            import clipboard    #for pasting copied instance
            from bs4 import BeautifulSoup

            #TODO set correct chromedriver path
            webdriverPath = os.path.join(BASE_DIR,"chromedriver")
            driver = webdriver.Chrome(webdriverPath)

            driver.get("https://server001.cloudehrserver.com/cot/opt/html_form_generator")

            fileinput = driver.find_element_by_id("validatedCustomFile")
            #get path of opt from system
            global path#path = "/home/rakshit/Documents/openEHR/vital_signs_summary.en.v1.opt"
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

            global data
            data = str(soup)

            #delete file from django(local)
            
            fs.delete(name)

            ##create new html file
            newfilepath = os.path.join(BASE_DIR,'templates')
            newfilepath = os.path.join(newfilepath,'form.html')
            newfileobject = open(newfilepath,"w+")

            #add button code to html
            htmlheadString ="""{% extends 'base.html' %}

            {% block head %}
            <title>Form</title>
            {% endblock %}

            {% block body %}
            """

            buttonString = """<div class="container">
            <form action="" method="post">
            {% csrf_token %}
            <input type="submit" name="Submit" value="Submit" />
            </form>
            </div>
            {% endblock %}
            """

            data = htmlheadString + data + "\n" + buttonString
            newfileobject.write(data)
            newfileobject.close()

            return redirect ('/form/')

    return render(request,'upload.html')


def py_form(request):
    if request.method == 'POST':
        ##TODO submit and send true false whether successful or not
        return redirect('/response/',{'flag': True})

    return render(request,'form.html')    

def py_response(request):
    if request.method == 'POST':
        return redirect('/upload/')
    return render(request,'response.html',{'flag':True})

