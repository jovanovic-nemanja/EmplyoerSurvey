

(function ($) {
    
    //Define visibleIndex for properties we want to show and set attribute that marks we want to show this property
    var maxVisibleIndex = 0;
    function showTheProperty(className, propertyName, visibleIndex) {
        if (!visibleIndex)
            visibleIndex = ++maxVisibleIndex;
        else {
            if (visibleIndex > maxVisibleIndex)
                maxVisibleIndex = visibleIndex;
            }
        //Use Survey Serializer to find the property, it looks for property in the class and all it's parents
        var property = Survey
            .Serializer
            .findProperty(className, propertyName)
        if (!property)
            return;
        property.visibleIndex = visibleIndex;
        //Custom JavaScript attribute that we will use in onShowingProperty event
        property.showProperty = true;
    }
    
    /*showTheProperty("question", "name");
    showTheProperty("question", "title");
    showTheProperty("question", "description");
    showTheProperty("question", "visible");
    showTheProperty("question", "required");
    showTheProperty("checkbox", "choices");
    showTheProperty("checkbox", "hasOther");
    showTheProperty("checkbox", "hasSelectAll");
    showTheProperty("checkbox", "hasNone");
    showTheProperty("text", "inputType");
    showTheProperty("text", "placeHolder");
    showTheProperty("comment", "placeHolder");
    showTheProperty("comment", "rows");
    
    var whitePropertyList = [
        "name",
        "title",
        "description",
        "visible",
        "isRequired",
        "choices",
        "hasOther",
        "hasSelectAll",
        "hasNone",
        "placeHolder",
        "rows",
        "inputType"
    ];
    
    //Use it to show properties that has our showProperty custom attribute equals to true
    creator
        .onShowingProperty
        .add(function (sender, options) {
            options.canShow = options.property.showProperty === true;
        });*/
    
    
    let saveNo_mark = 0
    // TODO: Minimal: https://surveyjs.io/Examples/Survey-Creator?id=singlepage&theme=bootstrap#content-js
    SurveyCreator
        .StylesManager
        .applyTheme("orange");
    
    //Remove default properties layout in property grid and have only one "general" category.
    SurveyCreator.SurveyQuestionEditorDefinition.definition = {};
    SurveyCreator.removeAdorners(["rating-item"]);
    Survey.Serializer.findProperty("rating", "rateMax").defaultValue = 10;
    /*SurveyCreator
        .SurveyQuestionEditorDefinition
        .definition["itemvalue[]@choices"]
        .tabs = [
            {
                name: "general",
                visible: false
            }
        ];*/
    /*Survey
        .Serializer
        .findProperty("cat", "cat")
        .readOnly = true;*/
    
    /*Survey.ComponentCollection.Instance.add({
      //Unique component name. It becomes a new question type. Please note, it should be written in lowercase.
      name: "country",
      //The text that shows on toolbox
      title: "Country",
      //The actual question that will do the job
      questionJSON: {
        type: "dropdown",
        optionsCaption: "Select a country...",
        choicesByUrl: {
          url: "https://restcountries.eu/rest/v2/all",
        },
      },
    });*/
    
    var curStrings = SurveyCreator.localization.getLocale("");
        curStrings.qt.rating = "Hiyer Rating";
    
    // creator.JsonObject.metaData.addProperty("questionbase", "cat");
    
    // Show Designer, Test Survey, JSON Editor and additionally Logic tabs
    var options = {
        showLogicTab: false,
        // show the embedded survey tab. It is hidden by default
        showEmbededSurveyTab: false,
        // hide the test survey tab. It is shown by default
        showTestSurveyTab: false,
        // hide the JSON text editor tab. It is shown by default
        showJSONEditorTab: false, //!in_production,
        // show the "Options" button menu. It is hidden by default
        showOptions: false, //!in_production,
        
        allowControlSurveyTitleVisibility: false,
        
        pageEditMode: "single",
        showTitlesInExpressions: true,
        allowEditExpressionsInTextEditor: false,
        showSurveyTitle: "always",
        questionTypes: [
            // "boolean",
            // "checkbox",
            // "radiogroup",
            // "dropdown",
            // "expression",
            // "matrix",
            // "matrixdynamic",
            // "panel",
            // "paneldynamic",
            "rating",
            // "matrixdropdown"
        ]
    };
    Survey.settings.allowShowEmptyTitleInDesignMode = false;
    Survey.settings.allowShowEmptyDescriptionInDesignMode = false;
    Survey.JsonObject.metaData.addProperty("survey", {
        name: "cat",
        type: "text",
    });
    
    //create the SurveyJS Creator and render it in div with id equals to "creatorElement"
    var creator = new SurveyCreator.SurveyCreator("creatorElement", options);
    
    // Remove toolbar items except undo/redo buttons
    creator
        .toolbarItems
        .splice(3, 3);
    // Set custom designer placeholder
    creator.placeholderHtml = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">' + '<img src="/images/dragToSurvey.svg" />' + '<div style="font-size: 20px; max-width: 210px;">' + 'Drag &amp; drop a Hiyer Rating question here to get started.' + '</div>' + '</div>';
    
    function load_creator_cache(_resp) {
        console.log('load_creator_cache', _resp)
        if(_resp.hasOwnProperty('draft_cache') && _resp.draft_cache !== null)
            creator.text = _resp.draft_cache
        if(_resp.hasOwnProperty('saved_surveys') && _resp.saved_surveys !== null){
            let load_txt = 'Survey bank empty'
            if(_resp.saved_surveys.length > 0)
                load_txt = 'Load a Survey'
            $('#saved_surveys_container').html(`<select id="survey_loader" class="form-control" title="Load a Survey"><option value="0">${load_txt}</option></select>`)
            for (let [key, value] of Object.entries(_resp.saved_surveys)) {
                console.log('surveys lvl 1:', key, value)
                for (let [k, v] of Object.entries(value)) {
                    console.log('surveys lvl 2:', k, v)
                    surveys[v.id] = {
                        id: v.id,
                        title: v.title,
                        json: v.json
                    }
                    let preload_sel = ''
                    if(v.id === survey_preload_id) {
                        preload_sel = ' selected '
                        try{
                            creator.text = JSON.stringify(surveys[v.id].json)
                        }catch{
                            creator.text = surveys[v.id].json
                        }
                    }
                    $('#survey_loader').append(`<option value="${v.id}" class="survey_load_item" ${preload_sel}>${v.title}</option>`)
                }
            }
            console.log(surveys)
        }
        creator.showDesigner()
        //creator.makeNewViewActive("designer")
    }
    
    let currently_loaded = 0
    $(document).on('click','#survey_loader',function(){
        //$('#preloader').show()
        //setTimeout($('#preloader').hide(), 5000)
        let _survey_id = $(this).val()
        if(_survey_id && surveys[_survey_id].hasOwnProperty('json')) {
            console.log(_survey_id, surveys[_survey_id].json)
            try {
                creator.text = JSON.stringify(surveys[_survey_id].json)
                alertify.success('Survey loaded.')
            }catch{
                try {
                    creator.text = surveys[_survey_id].json
                    alertify.success('Survey loaded.')
                }catch {
                    alertify.error('Could not load survey.')
                }
            }
            
        }
    });
    
    // ws_connect(load_creator_cache)
    ws_connect()
    creator
        .onCanShowProperty
        .add(function (sender, options) {
            if (options.obj.getType() == "survey") {
                let allowed_props = [
                    'title',
                    'category'
                ]
                options.canShow =  allowed_props.indexOf(options.property.name) !== -1;
            }
        });
    //Show toolbox in the right container. It is shown on the left by default
    creator.showToolbox = "right";
    //Show property grid in the right container, combined with toolbox
    creator.showPropertyGrid = "right";
    //Make toolbox active by default
    creator.rightContainerActiveItem("toolbox");
    let questionCounter = 1;
    creator
            .toolbarItems
            .destroyAll()
    creator
        .toolbarItems.unshift({
        id: "survey_cats_in",
        visible: true,
        data: { // data is the binding context for the template
            url: ko.computed(function () {
                return "/published?id=";
            })
        },
        template: "cats-template" // id of the tamplate, see HTML markup below
    });
    creator
        .onQuestionAdded
        .add(function (sender, options) {
            var q = options.question;
            var t = q.getType();
            console.log('q', q)
            console.log('t', t)
            q.cat = $('#cats').val()
            //q.name = "Question" + t[0].toUpperCase() + t.substring(1) + questionCounter;
            questionCounter++;
        });
    
    
    

    /*Survey
        .Serializer
        .addProperty("question", {
            name: "category",
            category: "general",
            readonly: true
        });*/
    
    var catEditor = {
        render: function (editor, htmlElement) {
            var input = document.createElement("select");
            input.className = "form-control svd_editor_control";
            input.style.width = "100%";
            input.id = 'category_prop'
            var option = document.createElement("option");
            input.add(option)
            for (let cat of survey_cats) {
                let this_option = document.createElement("option")
                this_option.text = cat.text;
                this_option.value = cat.id;
                input.add(this_option)
            }
            htmlElement.appendChild(input);
            input.onchange = function (_e) {
                console.log('onchange', _e)
                editor.koValue(input.value);
            }
            editor.onValueUpdated = function (newValue) {
                console.log('val updated', newValue)
                input.value = editor.koValue() || "";
            }
            input.value = editor.koValue() || "";
            
            $(input).select2({
                placeholder: "Set category",
                debug: !in_production
            })
        }
    };
    SurveyCreator
        .SurveyPropertyEditorFactory
        .registerCustomEditor("cat", catEditor);
    
    Survey
        .JsonObject
        .metaData
        .addProperty("question", {
            name: "cat",
            type: "cat",
            isRequired: true,
            category: "general",
            visibleIndex: 0,
            //choices: survey_cats
            template: "cats-template"
        });
    
    /*.toolbarItems
            .push({
                id: "custom-preview",
                visible: true,
                title: "Survey Preview",
                action: function () {
                    var testSurveyModel = new Survey.Model(creator.getSurveyJSON());
                    testSurveyModel.render("surveyContainerInPopup");
                    modal.open();
                }
            })*/
        //.properties
        /*.addProperty( "survey_cat", {
            name: "cat",
            isCopied: true,
            iconName: "icon-default",
            title: "Category",
            json: {
                "type": "dropdown",
                optionsCaption: "Category",
                choices: [
                    {
                        value: 1,
                        text: "Performance"
                    },
                    {
                        value: 2,
                        text: "Peer review"
                    },
                    {
                        value: 3,
                        text: "Managed up"
                    },
                    {
                        value: 4,
                        text: "CQI"
                    }
                ]
            }
        });*/
    
    creator.saveSurveyFunc = function(saveNo, callback) {
        // FIXME: Same survey saves as multiple save entires.
        //Save the survey definition into a local storage
        //window.localStorage.setItem("YourStorageName", surveyCreator.text);
        console.log('Saving survey', saveNo, creator.text);
        if(saveNo > saveNo_mark) {
            wscb.send({
                cmd: 'save_survey',
                survey_txt: creator.text
            }, function (resp) {
                if(resp.success)
                    saveNo_mark = saveNo
                console.log(resp)
                log_resp(resp);
                !!callback && callback(saveNo, resp.success);
            });
        }
    };
    console.log('creator options', creator.getOptions())
    $('#cats').select2({
        placeholder: "Set category",
        debug: !in_production
    });
    $('#cats').on('select2:select', function (e) {
        let data = e.params.data;
        console.log('select data', data);
        /*let qs = creator
            .survey
            .getAllQuestions()
        console.log('qs', qs)*/
        creator.survey.cat = data.id;
    });
    
    
    
})(window.jQuery)
