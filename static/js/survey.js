let this_survey,
    this_json,
    this_model;

(function ($) {
    ws_connect()
    
    if (survey_uuid !== null) {
        
        Survey.StylesManager.applyTheme("orange");  // bootstrap
    
        if (question_json !== undefined) {
            this_json = {
                "title": "test survey",
                "pages": [
                    {
                        "name": "page1",
                        "elements": [
                            question_json
                        ]
                    }
                ],
                "cat": "1"
            }
            this_model = new Survey.Model(JSON.stringify(this_json));
        } else if (survey_json !== undefined) {
            this_json = survey_json
            this_model = new Survey.Model(this_json)
        }
        
        this_survey = $("#surveyContainer").Survey({
            model: this_model,
            onComplete: function (data) {
                //console.log("send to server", data)
                wscb.send({
                    cmd: 'submit_answer',
                    survey_uuid: survey_uuid,
                    answer_json: data,
                    qid: question_id
                }, function (resp) {
                    log_resp(resp)
                })
            }
        })
    }
    
    $('.sv_complete_btn').wrap(`<div class="row"></div>`)
    $('.sv_complete_btn').parent().prepend(`<div class="col-xl-4 col-sm-4"></div>`)
    $('.sv_complete_btn').wrap(`<div class="col-xl-4 col-sm-4"></div>`)
    $('.sv_complete_btn').parent().append(`<div class="col-xl-4 col-sm-4"></div>`)
    
    $('.sv_p_root').wrap(`<div class="row"></div>`)
    $('.sv_p_root').parent().prepend(`<div class="col-xl-4 col-sm-4"></div>`)
    $('.sv_p_root').wrap(`<div class="col-xl-4 col-sm-4"></div>`)
    $('.sv_p_root').parent().append(`<div class="col-xl-4 col-sm-4"></div>`)
    
})(window.jQuery)
