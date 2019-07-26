from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
import os
from selenium import webdriver
import clipboard    #for pasting copied instance
from bs4 import BeautifulSoup
from django.conf import settings


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#path of uploaded file
path = ""

#path of file to be validated
vpath = ""
savedFormPath = ""
data = ""
webdriverPath = os.path.join(BASE_DIR,'chromedriver')

def home(request):
    return render(request, 'home.html')


def py_upload(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('document',False)
        if(uploaded_file): #if file selected and is .opt
            if(not str(uploaded_file).endswith('.opt')):
                error = """
                <div class="alert alert-danger" role="alert">
                Please select .opt file
                </div>"""
                return render(request, 'upload.html',{'error':error})

            else:
                ##OPT TO FILE START##
                fs = FileSystemStorage()
                name = fs.save(uploaded_file.name, uploaded_file)
                global path
                renamedFileName , path = TemplateIDRename(name)

                #path = fs.path(name)

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

                #delete original uploaded file from django(local)
                fs.delete(name)
                #delete file with modified template id
                fs.delete(renamedFileName) 

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
                ##OPT TO FILE END##               

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

        # converting the saved html to json
        import json
        def findDiv(div):
        	divs = div.findChildren('div', recursive = False)
        	headings = div.findChildren('h1')
        	labels = div.findChildren('label', recursive = False)
        	if (len(labels)!=0):
        	    label = labels[0].text
        	    if(len(headings)!=0):
        	    	label = headings[0].text
        	else:
        		Str = ""
        		for st in div['class']:
        			Str += st
        		label = Str
        	if(len(divs)==0):
        		ans = []
        		inputs = div.findChildren('input')
        		if(len(inputs)!=0):
        			for ip in inputs:
        				try:
        					ans.append(rules[ip['name']])
        				except KeyError:
        					pass
        		selects = div.findChildren('select')
        		if(len(selects)!=0):
        			for select in selects:
        				options = select.findChildren('option', {'selected':"selected"})
        				for option in options:
        					ans.append(option.text)
        		if(len(labels)!=0):
        			finalAns = {}
        			finalAns[label] = ans
        		else:
        		    finalAns = ans
        		return finalAns

        	else: # if it contains sub divisions
        		ans = {}
        		for div in divs:
        			if(label not in ans):
        				ans[label] = [findDiv(div)]
        			else:
        				ans[label].append(findDiv(div))
        		return ans

        div = soup.find_all('div', {'class':"OBSERVATION"})  # Set the division from which you want to store the file
        Ans = findDiv(div[0])
        newJSON = json.dumps(Ans)
        loadedJSON = json.loads(newJSON)

        jsonForm = os.path.join(BASE_DIR,'media')
        jsonForm = os.path.join(jsonForm,'savedForm.json')
        jsonFormObject = open(jsonForm,"w+")
        json.dump(loadedJSON, jsonFormObject)
        jsonFormObject.close()


        return redirect('/response/')

    return render(request,'form.html')    

def py_response(request):
    if request.method == 'POST':
        if('rhome' in request.POST):
            return redirect('/')
        if('rvalidate' in request.POST):    
            print(request.POST.get('value'))
            Validate(filepath= savedFormPath)
            return redirect('/validator_response/')
    return render(request,'response.html')


def py_validate(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('document',False)
        if(uploaded_file): #if file is selected and is XML or HTML
            if(str(uploaded_file).endswith('.xml') or str(uploaded_file).endswith('.html')):
                fs = FileSystemStorage()
                savedFile = fs.save(uploaded_file.name, uploaded_file)
                global vpath
                vpath = fs.path(savedFile)
                Validate(filepath = vpath)
                fs.delete(savedFile)
                return redirect('/validator_response/')
            else:
                error = """
                <div class="alert alert-danger" role="alert">
                Please select .xml or .html file
                </div>"""
                return render(request, 'validate.html',{'error':error})

    return render(request,'validate.html')        


def py_validator_response(request):
    if request.method == 'POST':
        ##give choice to go to home or 
        return redirect('/')
    return render(request,'validator_response.html') 



##HELPER FUNCTIONS##
def Validate(filepath):
    global webdriverPath
    driver = webdriver.Chrome(executable_path = webdriverPath)
    driver.get("https://server001.cloudehrserver.com/cot/opt/xml_instance_validator")

    fileinput = driver.find_element_by_id("validatedCustomFile")
    #get path of opt from system
    #global path
    fileinput.send_keys(filepath)
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
                <input type="submit" name="valid" value="Home" />
                
            </form>
        </div>
    """
    source_code = htmlheadString + "\n"+ str(soup) + "\n"+ buttonString
    newfilepath = os.path.join(BASE_DIR,'templates')
    newfilepath = os.path.join(newfilepath,'validator_response.html')
    newfileobject = open(newfilepath,"w+")
    newfileobject.write(source_code)
    newfileobject.close()


def TemplateIDRename(savedFile):
    ##takes in relative of file inside /media/ and returns new file's name and full path
    filename = str(savedFile).split('.')[0]
    filepath = os.path.join(settings.MEDIA_ROOT, savedFile)
    fileObject = open(filepath, "r+")
    content = fileObject.read()
    for symbol in filename:
        if (symbol!=' ' and symbol.isalnum()==False):
            filename = filename.replace(symbol,'')
    filename = filename.replace(" ","_")
    filename = filename+'.en'+'.v1' #TODO  +str(versionNumber)
    filename = filename.lower()
    soup = BeautifulSoup(content,'html.parser')
    idElements = soup.find_all('template_id')
    for element in idElements:
        #element.string.replace_with(filename+'.en'+'.v1')
        valueElement = element.findChild() #returns first child of element
        valueElement.string.replace_with(filename)
    newContent = str(soup)
    newfilepath = os.path.join(settings.MEDIA_ROOT,filename+".opt")
    fileObject.close()
    fileObject = open(newfilepath,'w+')
    fileObject.write(newContent) 
    fileObject.close
    filename += ".opt"
    return filename, newfilepath

