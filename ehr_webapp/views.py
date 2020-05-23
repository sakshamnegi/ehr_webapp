from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import HttpResponse, Http404
import os
from selenium import webdriver
import clipboard    #for pasting copied instance
from bs4 import BeautifulSoup
from django.conf import settings
from lxml import etree
import json

#trying headless chrome \\TODO
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#path of uploaded file
path = ""
filename = ""

#path of file to be validated
vpath = ""
savedFormPath = ""
data = ""
chrome_options = webdriver.ChromeOptions()

# for retrieval purposes
pid = ""

#Only for Local.. COMMENT OUT FOR HEROKU
# webdriverPath = os.path.join(BASE_DIR,'chromedriver.exe')  #replace with chromedriver.exe for windows

#Only for heroku.. COMMENT OUT FOR LOCAL
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BINARY")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")

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
                #Only for Local.. COMMENT OUT FOR HEROKU
                # driver = webdriver.Chrome(executable_path = webdriverPath)

                #Only for Heroku.. COMMENT OUT FOR LOCAL
                driver = webdriver.Chrome(executable_path = os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
                
                driver.get("https://server001.cloudehrserver.com/cot/opt/html_form_generator")
                fileinput = driver.find_element_by_id("validatedCustomFile")
                #get path of opt from system
                #global path
                fileinput.send_keys(path)

                submitbutton = driver.find_element_by_name("doit")
                submitbutton.click()
                element = driver.find_element_by_xpath("/html/body/div[1]/div/div/div/section/div/div/div")
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
                    <body style="margin-left: 30px;margin-right:30px">
                <form action="" method="post">
                    {% csrf_token %}
                """

                buttonString = """<div class="container">
                <div class="input-group-prepend">
                    <span class="input-group-text" id="basic-addon1">Patient ID</span>
                    <input  id="patient_id" type="text" class="form-control" placeholder="Patient ID" aria-label="Username" 
                        aria-describedby="basic-addon1" required="true" name="patient_id"
                        pattern="[a-zA-Z0-9]{6,}$"title="Patient ID must have atleast 6 characters(only letters/numbers allowed)">
                </div>
                <br><br>
                <input type="submit" name="Submit" value="Submit" />
                <br><br>
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
                            if(rules[ip['name']]!=""):ans.append(rules[ip['name']])
                        except KeyError:
                            pass
                selects = div.findChildren('select')
                if(len(selects)!=0):
                    for select in selects:
                        options = select.findChildren('option', {'selected':"selected"})
                        for option in options:
                            if(option.text!=""):ans.append(option.text)
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


        try:
            patientId = str(rules["patient_id"][0])#str(request.GET.get("patient_id"))#soup.find("input",{"id": "patient_id"}).get("value")
            print("PID ", patientId)
        except:
            print("Error while retrieving patient id")
            

        #saving file in mongodb
        import pymongo
        from pymongo import MongoClient
        from datetime import datetime
        from pytz import timezone

        client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
        db = client[patientId]
        cTag = soup.find('div', {'class':"container"})
        cName = cTag.h1.text
        posts = db[cName]

        #converting to json
        div = soup.find_all('div', {'class':"OBSERVATION"})  # Set the division from which you want to store the file
        Ans = findDiv(div[0])
        # changing name of the file
        global filename
        Ans['name'] = filename[:-5] + str(posts.count() + 1)# error will be generated for file saved before connection is made. Make sure your ip is in whitelist of mongodb atlas
        # if the step of conversion of opt to form is bypassed and form is submitted by going back from response page - the name will be "1", "2" ... , because filename variable will be empty
        tempDate = str(datetime.now(timezone('Asia/Kolkata')))
        Ans['date'] = tempDate[:10]
        newJSON = json.dumps(Ans)
        loadedJSON = json.loads(newJSON)

        jsonForm = os.path.join(BASE_DIR,'media')
        jsonForm = os.path.join(jsonForm,'savedForm.json')
        jsonFormObject = open(jsonForm,"w+")
        json.dump(loadedJSON, jsonFormObject)
        jsonFormObject.close()
        
        # continuing with mongodb
        #posts.drop()
        posts.create_index([('name', pymongo.ASCENDING)], unique=True)
        try:
            posts.insert_one(loadedJSON)
        except:
            print("Document with same name already present")

            
        return redirect('/response/')

    return render(request,'form.html')    

def py_response(request):
    if request.method == 'POST':
        if('rhome' in request.POST):
            return redirect('/')
        #removing validation option from saved document    
        #if('rvalidate' in request.POST):    
            #print(request.POST.get('value'))
            #Validate(filepath= savedFormPath)
            #return redirect('/validator_response/')
    return render(request,'response.html')


def py_validate(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('document',False)
        if(uploaded_file): #if file is selected and is XML or HTML
            if(str(uploaded_file).endswith('.xml') or str(uploaded_file).endswith('.html')):
                fs = FileSystemStorage()
                savedFile = fs.save(uploaded_file.name, uploaded_file)
                global filename
                filename = uploaded_file.name
                global vpath
                vpath = fs.path(savedFile)
                #new validation code
                schema_folder = os.path.join(BASE_DIR,'media')
                xsd_path = schema_folder + '/' + "complete_version.xsd"
                print(xsd_path)
                Validate(xml_filepath = vpath,xsd_path = xsd_path)
                #fs.delete(savedFile)
                return redirect('/validator_response/')
            else:
                error = """
                <div class="alert alert-danger" role="alert">
                Please select .xml file
                </div>"""
                return render(request, 'validate.html',{'error':error})

    return render(request,'validate.html')        


def py_validator_response(request):
    if request.method == 'POST':
        if('Home' in request.POST):
            return redirect('/')
        if('Save' in request.POST):
            ##CONVERT xml (file path in global variable 'vpath') to json 
            #getting patientID from post values
            import ast
            import json
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

            rules = ast.literal_eval(POSTdata)
            try:
                patientId = str(rules["patient_id"][0])
                print("PID ", patientId)
            except:
                print("Error while retrieving patient id")

            # converting xml to json
            import xmlschema
            schema_folder = os.path.join(BASE_DIR,'media')
            xsd_path = schema_folder + '/' + "complete_version.xsd"
            xs = xmlschema.XMLSchema(xsd_path)
            global vpath
            newDict = xs.to_dict(vpath)
            fs = FileSystemStorage()
            fs.delete(vpath)

            # saving to mongodb atlas
            import pymongo
            from pymongo import MongoClient
            from datetime import datetime
            from pytz import timezone

            client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
            db = client[patientId]
            global filename
            try:
                cName = newDict["data"]["archetype_details"]["template_id"]["value"]
                stemp = ""
                stemp += cName[:-6]
                stemp =  stemp.replace('_', ' ')
                stemp = stemp.title()
                posts = db[stemp]
                newDict['name'] = cName[:-1] + str(posts.count() + 1)
            except:
                cName = newDict["data"]["name"]["value"]# if template id is present -> ["archetype_details"]["template_id"]["value"]
                posts = db[cName]
                newDict['name'] = newDict["data"]["@archetype_node_id"][:-2] + newDict["data"]["language"]["code_string"] + ".v" + str(posts.count() + 1)

            tempDate = str(datetime.now(timezone('Asia/Kolkata')))
            newDict['date'] = tempDate[:10]

            newJSON = json.dumps(newDict)
            loadedJSON = json.loads(newJSON)
            jsonForm = os.path.join(BASE_DIR,'media')
            jsonForm = os.path.join(jsonForm,'savedForm.json')
            jsonFormObject = open(jsonForm,"w+")
            json.dump(loadedJSON, jsonFormObject)
            jsonFormObject.close()

            posts.create_index([('name', pymongo.ASCENDING)], unique=True)
            try:
                posts.insert_one(loadedJSON)
            except:
                print("Document with same name already present")
            ##get patient id and save
            return render(request, 'response.html') 
        
    return render(request,'validator_response.html') 

collections = []
def py_retrieve(request):
    if request.method == 'POST':
        if('pid' in request.POST):
            global pid
            ## get names of collections available for this patient from atlas  and store in collections array below 
            pid = request.POST.get('patient_id')
            import pymongo
            from pymongo import MongoClient
            client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
            db = client[pid]
            global collections 
            collections = db.list_collection_names()

            #if patient doesn't exist
            if not collections:
                return redirect('/no_record/')
            #if patient data exists open retrieval type html
            else:
                return render(request,'choose_retrieval.html',{'pid':pid, 'collections': collections})
        
        if('get_ehr' in request.POST):
            # creating dictionary of collections within the database 'pid'
            import pymongo
            from bson import json_util
            import json
            from pymongo import MongoClient
            client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
            db = client[pid]
            collections = db.list_collection_names()
            ans = {}
            for i in collections:
                cl = db[i]
                cursor = cl.find({})
                cans = []
                for doc in cursor:
                    #for key in doc: # onject of type ObjectID is not JSON serializable
                        #doc[key] = str(doc[key]) # ID of each document is ObjectID type 
                    cans.append(doc)
                ans[i] = cans

            #converting dictionary to json
            newJSON = json.dumps(ans, default=json_util.default)
            loadedJSON = json.loads(newJSON)
            jsonForm = os.path.join(BASE_DIR,'media')
            jsonForm = os.path.join(jsonForm,'savedEHR.json')
            jsonFormObject = open(jsonForm,"w+")
            json.dump(loadedJSON, jsonFormObject, indent = 4)
            jsonFormObject.close()

            return redirect('/retrieval_response/')
            #create document with all ehrs here
            
        if('get_composition' in request.POST):
            requestedCollection = request.POST.get('composition_id')
            if(requestedCollection == 'Choose Composition...'):
                #render page again with error message
                error = """
                <div class="alert alert-danger" role="alert">
                Please choose a composition from list 
                </div>"""
                print(pid)
                return render(request, 'choose_retrieval.html',{'pid':pid,'error':error, 'collections': collections})
            print(requestedCollection)
            #get collection corresponding to requestedCollection
            import pymongo
            from bson import json_util
            import json
            from pymongo import MongoClient
            client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
            db = client[pid]
            cl = db[requestedCollection]
            cursor = cl.find({})
            requestedDoc = cursor[cl.count()-1]

            newJSON = json.dumps(requestedDoc, default=json_util.default)
            loadedJSON = json.loads(newJSON)
            jsonForm = os.path.join(BASE_DIR,'media')
            jsonForm = os.path.join(jsonForm,'savedEHR.json')
            jsonFormObject = open(jsonForm,"w+")
            json.dump(loadedJSON, jsonFormObject, indent = 4)
            jsonFormObject.close()

            return redirect('/retrieval_response/')


        if('get_composition_after' in request.POST):
            requestedCollection = request.POST.get('composition_id2')
            if(requestedCollection == 'Choose Composition...'):
                #render page again with error message
                error = """
                <div class="alert alert-danger" role="alert">
                Please choose a composition from list
                </div>"""
                print(pid)
                return render(request, 'choose_retrieval.html',{'pid':pid,'error':error, 'collections': collections})
            requestedDate = request.POST.get('date')
            import pymongo
            from bson import json_util
            import json
            from pymongo import MongoClient
            client = MongoClient('mongodb+srv://RDJ:rdjpass@cluster0-4wly7.azure.mongodb.net/test?retryWrites=true&w=majority')#('mongodb://localhost:27017/')
            db = client[pid]
            cl = db[requestedCollection]
            cursor = cl.find({})
            requestedDoc = {}
            docGroup = []
            for doc in cursor:
                try:
                    if(doc['date']>=requestedDate):
                        docGroup.append(doc)
                except:
                    continue
            if(len(docGroup)==0):
                return redirect('/no_record/')
            requestedDoc[requestedCollection] = docGroup

            newJSON = json.dumps(requestedDoc, default=json_util.default)
            loadedJSON = json.loads(newJSON)
            jsonForm = os.path.join(BASE_DIR,'media')
            jsonForm = os.path.join(jsonForm,'savedEHR.json')
            jsonFormObject = open(jsonForm,"w+")
            json.dump(loadedJSON, jsonFormObject, indent = 4)
            jsonFormObject.close()
            # change redirect url to retrieval_response once done
            # TODO 
            return redirect('/retrieval_response/')
        else:
            #display no record found page  
            return redirect('/no_record/')
            
    return render(request, 'retrieve.html')


def py_retrieval_response(request):
    form = os.path.join(BASE_DIR,'media')
    form = os.path.join(form,'savedEHR.json')
    formObject = open(form)
    data = json.load(formObject)
    keys = data.keys()
    formObject.close()
    if request.method == 'POST':
        if('download_ehr_json' in request.POST):
            ##download json file
            try:
                file_name = data['name']
            except:
            	file_name = pid + "_all_EHRs"#get the filename of desired file
            path_to_file = form #get the path of desired  file
            file_path = form
            file_name +=".json"
            if os.path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type="application/json")
                    response['Content-Disposition'] = 'attachment; filename=' + file_name 
                    return response
            raise Http404
            print("Downloading ehr json")
    return render(request,'retrieval_response.html', {'data':data})


def py_no_record(request):
    if request.method == 'POST':
        if('home' in request.POST):
            return redirect('/')
        if('tryagain' in request.POST):
            return redirect('/retrieve/')
    return render(request,'no_record.html')

##HELPER FUNCTIONS##
def Validate(xml_filepath,xsd_path):
    
    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    log_text = """<div class="jumbotron">
    <h1>Validation Result</h1>
    </div>
    """
    # parse xml
    try:
        xml_doc = etree.parse(xml_filepath)
        log_text += """<h3>XML Syntax validation : </h3>
            <div class="alert alert-success"> Okay </div>"""

    # check for file IO error
    except IOError:
        log_text += """<div class="alert alert-danger"> Invalid XML file </div>"""

    # check for XML syntax errors
    except etree.XMLSyntaxError as err:
        log_text += """<h2>XML Syntax Error</h2> <ul class="list-group">"""
        for error in err.error_log:
            log_text += "<li class=\"list-group-item\">" + "ERROR ON LINE " + str(error.line) + " " + str(error.message.encode("utf-8")) + "</li>"
        log_text += "</ul>"
    except:
        log_text += 'Unknown error occurred .\n'
        

    # validate against schema
    try:
        xmlschema.assertValid(xml_doc)
        log_text += """<h3>XML Schema validation : </h3>
            <div class="alert alert-success"> Okay </div>"""

    except etree.DocumentInvalid as err:
        log_text += "<h3>XML Validation Error :</h3> <ul class=\"list-group\">"
        for error in err.error_log:
            log_text += "<li class=\"list-group-item\">" + "ERROR ON LINE " + str(error.line) + " " + str(error.message.encode("utf-8")) + "</li>"
        log_text += "</ul>"

    except:
        log_text += 'Unknown error occurred .\n'
        
    result = xmlschema.validate(xml_doc)
    if(result):
        log_text += """<div class="alert alert-success"> <strong> Instance is valid :)</strong>
        </div>
        <div class="input-group-prepend">
                    <span class="input-group-text" id="basic-addon1">Patient ID</span>
                    <input  id="patient_id" type="text" class="form-control" placeholder="Patient ID" aria-label="Username" 
                        aria-describedby="basic-addon1" required="true" name="patient_id"
                        pattern="[a-zA-Z0-9]{6,}$"title="Patient ID must have atleast 6 characters(only letters/numbers allowed)">
                </div>
                <br>
                <input type="submit" name="Save" value="Save" />
                <br><br>
        """

    else:
        log_text += """<div class="alert alert-danger"> <strong> Instance is invalid :(</strong>
        </div>"""

    log_text += "</form>"

    htmlheadString ="""<!DOCTYPE html>
        <html>
            <head>
                <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
                <title>Validator Response</title>
            </head>
            <body style="margin-left: 30px;margin-right:30px">
        <form action="" method="post">
            {% csrf_token %}
        """

    buttonString = """<div>
        <form action="" method="post">
                {% csrf_token %}
                <input type="submit" name="Home" value="Home" />
                
            </form>
        </div>
        </body> </html>

    """
    source_code = htmlheadString + "\n"+ log_text + "\n"+ buttonString
    newfilepath = os.path.join(BASE_DIR,'templates')
    newfilepath = os.path.join(newfilepath,'validator_response.html')
    newfileobject = open(newfilepath,"w+")
    newfileobject.write(source_code)
    newfileobject.close()


def TemplateIDRename(savedFile):
    ##takes in relative of file inside /media/ and returns new file's name and full path
    filepath = os.path.join(settings.MEDIA_ROOT, savedFile)
    fileObject = open(filepath, "r+")
    content = fileObject.read()
    soup = BeautifulSoup(content,'html.parser')
    conceptElement = soup.find('concept')

    global filename
    filename = conceptElement.text
    for symbol in filename:
        if (symbol!=' ' and symbol.isalnum()==False):
            filename = filename.replace(symbol,'')
    filename = filename.replace(" ","_")
    filename = filename+'.en'+'.v1' #TODO  +str(versionNumber)
    filename = filename.lower()
    
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

