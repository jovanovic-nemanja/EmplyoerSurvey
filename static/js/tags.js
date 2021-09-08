// #3A43BA
let tagifyInv,
    addAllSuggestionsElm,
    deptsIn,
    invitesEl,
    addInvBtn
let tags_loaded = {}
let controller,
    tag_wlst = []
const reg_tag = function (t) {
    console.log('Registered tag:', t)
}
let mail_phone_toggle = true


function getRandomColor() {
    function rand(min, max) {
        return min + Math.random() * (max - min);
    }
    
    let h = rand(1, 360) | 0,
        s = rand(40, 70) | 0,
        l = rand(65, 72) | 0;
    
    return 'hsl(' + h + ',' + s + '%,' + l + '%)';
}


function observe(sel, cb) {
    const targetNode = $(sel)
    // Options for the observer (which mutations to observe)
    const config = {attributes: true, childList: true, subtree: true}
    // Callback function to execute when mutations are observed
    const callback = function (mutationsList, observer) {
        // Use traditional 'for loops' for IE 11
        for (const mutation of mutationsList) {
            if (mutation.type === 'childList') {
                console.log('A child node has been added or removed.')
            } else if (mutation.type === 'attributes') {
                console.log('The ' + mutation.attributeName + ' attribute was modified.')
            }
            cb(mutation)
        }
    }
    // Create an observer instance linked to the callback function
    const observer = new MutationObserver(callback)
    // Start observing the target node for configured mutations
    observer.observe(targetNode, config);
    return observer
}


function observe_additions(sel, cb) {
    let obs = new MutationObserver(function (mutations, observer) {
        // using jQuery to optimize code
        $.each(mutations, function (i, mutation) {
            let addedNodes = $(mutation.addedNodes)
            let selector = "span.stuff"
            let filteredEls = addedNodes.find(selector).addBack(selector) // finds either added alone or as tree
            filteredEls.each(function () { // can use jQuery select to filter addedNodes
                console.log('Insertion detected: ' + $(this).text())
            })
        })
    })
    let canvasElement = $(sel)[0]
    obs.observe(canvasElement, {childList: true, subtree: true})
    return obs
}


function ignore(observer) {
    // later, you can stop observing
    observer.disconnect()
}


function getIfSet(variable) {
    return (typeof variable !== typeof undefined) ? variable : undefined
}


const TagChooser = (inputEl, tagifyOpts = {},
                    loadIcons = false,
                    wsSender= '',
                    onAddCb=function(tag){}) => {
    //const getInputEl = () => inputEl
    //const getTagifyOpts = () => tagifyOpts
    //const getParam = (param) => getIfSet(param)
    console.log(`Initialized TagChooser for ${inputEl.id}. loadIcons:`, loadIcons)
    const init = (tagLimit= false, tagType = 'tags') => {
        const fn = this
        this.tagType = tagType
        // section addCard
        this.addCard = function(tag) {
            if (tag.type !== 'tags') {
                return
            }
            tag.bgcolor = $(fn.tagify.getTagElmByValue(tag.slug)).attr('bgcolor')
            tag.color = $(fn.tagify.getTagElmByValue(tag.slug)).attr('color')
            $('#departments').prepend(`<div class="orgcard-container tag_${tag.slug}" style="background-color: ${tag.bgcolor};">
              <input class="orgcard" id="tag_${tag.slug}" type="checkbox" name="${tag.slug}" value="${tag.bgcolor}" style="background-color: ${tag.color};">
              <label class="orgcard" for="tag_${tag.slug}" style="background-color: ${tag.bgcolor}; color: ${tag.color}"><span>${tag.name}</span></label>
            </div>`)
        }
        
        this.fillIconBox = (_tag, elid) => {
            const el =$(`#${elid}`)
            el.text('')
            el.css('padding-top', 3)
            el.html(`<span class="iconify" data-icon="${_tag.prefix}:${_tag.slug}"></span>`)
            // console.log('fill', _tag)
        }
        
        this.addTag = function (e) {
            let tag_bgcolor = $(e.detail.tag).attr('bgcolor')
            let tag_color = $(e.detail.tag).attr('color')
            console.log('tagbg', tag_bgcolor);
            let tag = {
                name: e.detail.data.value,
                slug: e.detail.data.value.replaceAll(' ', '-'),
                type: fn.tagType
            }
            console.log('Adding tag', tag)
            // if(!departments.find(el => el.slug === tag.slug)) {
            //console.log('Add Dept:', tag.)
            if (wsSender === 'add_dept'){
                wscb.send({
                    cmd: 'add_dept',
                    dept: tag
                }, function(_resp){
                    log_resp(_resp)
                    if (_resp.success) {
                        fn.addCard(tag)
                        $('#invite_dept').append(`<option value="${tag.id}">${tag.name}</option>`)
                        $('.depts').append(`<span class="badge badge-secondary">${tag.name}</span>&nbsp;`)
                    }
                })
            }
            
            if (loadIcons){
                console.log('loadIcons:', loadIcons)
                wscb.send({
                    cmd: 'icon_insta',
                    icon: tag.slug,
                    icon_color: tag_bgcolor
                }, function (resp) {
                    console.log(`Icon response for "${tag.slug}":`, resp)
                    if (resp.icons) {
                        console.log('Following through with resp.icons')
                        for (const [i, lib] of Object.entries(resp.icons)) {
                            console.log('lib:', lib)
                            console.log('i:', i)
                            console.log('tag:', tag)
                            if ((lib.hasOwnProperty('icons') && lib.icons.hasOwnProperty(tag.slug)) || (lib.hasOwnProperty('slug') && lib.slug === tag.slug)) {
                                console.log('Settled on icon:', lib.prefix, ':', tag.slug)
                                tag.prefix = lib.prefix
                                // console.log('Settled on icon:', tag.tag, 'lib:', lib, 'full:', lib.icons[tag.tag].body)
                                // `<svg class="svg-inline--fa fa-chart-line fa-w-16" aria-hidden="true" focusable="false" data-prefix="fa" data-icon="chart-line" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" data-fa-i2svg=""><path fill="currentColor" d="M496 384H64V80c0-8.84-7.16-16-16-16H16C7.16 64 0 71.16 0 80v336c0 17.67 14.33 32 32 32h464c8.84 0 16-7.16 16-16v-32c0-8.84-7.16-16-16-16zM464 96H345.94c-21.38 0-32.09 25.85-16.97 40.97l32.4 32.4L288 242.75l-73.37-73.37c-12.5-12.5-32.76-12.5-45.25 0l-68.69 68.69c-6.25 6.25-6.25 16.38 0 22.63l22.62 22.62c6.25 6.25 16.38 6.25 22.63 0L192 237.25l73.37 73.37c12.5 12.5 32.76 12.5 45.25 0l96-96 32.4 32.4c15.12 15.12 40.97 4.41 40.97-16.97V112c.01-8.84-7.15-16-15.99-16z"></path></svg>`
                                // $(`#tag_ico_${tag.tag}`).append(`<svg class="" style="height: ${lib.info.height}px;width: ${lib.info.width}px" enable-background="new 0 0 500 500" aria-hidden="true" focusable="false" data-prefix="${lib.prefix}" data-icon="${lib.prefix}" role="img" xmlns="http://www.w3.org/2000/svg">${lib.icons[tag.tag].body}</svg>`)
                                console.log('fn.tagType', fn.tagType)
                                if(fn.tagType === 'tags'){
                                    $(`#tag_ico_${tag.slug}`).append(`<span class="iconify" data-icon="${lib.prefix}:${tag.slug}" style="background-color: ${tag_bgcolor}"></span>`)
                                    tag.prefix = lib.prefix
                                    Iconify.scan($(`#tag_ico_${tag.slug}`))
                                }
                                break
                            }
                        }
                    } else {
                        console.log('need question mark')
                        console.log('qmarkspot', tag)
                        $(`#tag_ico_${tag.slug}`).append(`<span class="iconify" data-icon="emojione-v1:question-mark" data-color=""></span>`)
                        fn.addCard(tag)
                        Iconify.scan($(`#tag_ico_${tag.slug}`))
                    }
                    onAddCb(tag, fn)
                })
            }
            
            /*}else{
                $(`#tag_${tag.slug}`).prop("checked", true)
            }*/
        }
        
        this.suggestIcon = function (tagData) {
            console.log('Suggesting Icon becase loadIcons =', loadIcons)
            console.log('tagData:', tagData)
            let tag = tagData // tagData.hasOwnProperty('slug') ? tagData['slug'] : tagData.value
            return `
        <div ${this.getAttributes(tagData)}
            class='tagify__dropdown__item ${tagData.class ? tagData.class : ""}'
            tabindex="0"
            role="option">
            ${tag ? `
            <div class='tagify__dropdown__item__avatar-wrap'>
                <span class="iconify" data-icon="${tag.prefix}:${tag.slug}"></span>
                <!--<span class='tagify__tag-text' style="">${tag}</span>-->
                <!--<img onerror="this.style.visibility='hidden'" src="${tagData.avatar}">-->
            </div>` : ''
            }
            <strong>${tag.slug}</strong>
            <!--<span>${tag.slug}</span>-->
        </div>
    `;
        }
        
        this.transformTag = function (tagData) {
            tagData.style = "--tag-bg:" + getRandomColor();
            
            if (tagData.value.toLowerCase() == 'shit')
                tagData.value = 's✲✲t'
        }
        
        this.onInvalidTag = (e) => {
            alertify.error(`"<b>${e.detail.data.value}</b>" isn't a valid email address or int. phone number`);
        }
        
        this.suggestTag = function (tagData) {
            console.log('Suggesting Tag becase loadIcons =', loadIcons)
            console.log('tagData2:', tagData)
            let tag = tagData // tagData.hasOwnProperty('slug') ? tagData['slug'] : tagData.value
            return `
        <div ${this.getAttributes(tagData)}
            class='tagify__dropdown__item ${tagData.class ? tagData.class : ""}'
            tabindex="0"
            role="option">
            ${tag ? `
<!--            <div class='tagify__dropdown__item'>-->
<!--                <span class="iconify" data-icon="${tag.prefix}:${tag.slug}"></span>-->
                <!--<span class='tagify__tag-text' style="">${tag}</span>-->
                <!--<img onerror="this.style.visibility='hidden'" src="${tagData.avatar}">-->
<!--            </div>-->` : ''
            }
            <strong>${tag.slug}</strong>
            <!--<span>${tag.slug}</span>-->
        </div>
    `;
        }
        
        this.tagIconTemplate = function (tagData) {
            console.log('tagData', tagData)
            let bgcolor
            if (tagData.hasOwnProperty('bgcolor')) {
                bgcolor = tagData.bgcolor
            } else {
                bgcolor = tag_colors[Math.floor(Math.random() * tag_colors.length)]
            }
            let tag_slug = tagData.name || tagData.email
            tag_slug = tag_slug.replaceAll(' ', '-')
            return `
        <tag title="tag_${tag_slug}"
                id="${tag_slug}"
                contenteditable='false'
                spellcheck='false'
                tabIndex="-1"
                bgcolor='${bgcolor}'
                color="${lightOrDark(bgcolor) ? 'black' : 'white'}"
                style="--tag-bg: ${bgcolor} !important;--tag-text-color: ${lightOrDark(bgcolor) ? 'black' : 'white'};--tag-hover: ${bgcolor};--tag-remove-btn-bg--hover: ${bgcolor};--tag-remove-btn-bg: ${bgcolor};--tag-remove-bg: ${bgcolor}"
                class="${this.settings.classNames.tag} ${tagData.class ? tagData.class : ''}"
                ${this.getAttributes(tagData)}>
            <x style="color: ${lightOrDark(bgcolor) ? 'black' : 'white'};background-color: ${bgcolor};" title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
            <div style="">
                <div id="tag_${tag_slug}_wrap" class="tagify__tag__avatar-wrap" style="background-color: ${tagData.color};">
                <span id="tag_ico_${tagData.name}" style="color: ${lightOrDark(bgcolor) ? 'black' : 'white'}; background-color: ${bgcolor};">
                    <!--<i class="fa fa-${tagData.fa}"></i>-->
                </span>
                    <!--<img onerror="this.style.visibility='hidden'" src="${tagData.avatar}">-->
                </div>
                <span class='tagify__tag-text' style="">${tag_slug}</span>
            </div>
        </tag>
    `;
        }
        
        this.getAddAllSuggestionsElm = function() {
            // suggestions items should be based on "dropdownItem" template
            return tagLimit ? undefined : this.tagify.parseTemplate('dropdownItem', [{
                class: "addAll",
                name: "Add all",
                slug: "Add All",
                email: this.tagify.settings.whitelist.reduce(function (remainingSuggestions, item) {
                    return this.tagify.isTagDuplicate(item.value) ? remainingSuggestions : remainingSuggestions + 1;
                }, 0) + " Tags"
            }])
        }
        
        this.onSelectSuggestion = (e) => {
            if (e.detail.elm === addAllSuggestionsElm)
                this.tagify.dropdown.selectAll.call(this.tagify);
        }
        
        this.onDropdownShow = function(e) {
            console.log(e)
            let dropdownContentElm = e.detail.tagify.DOM.dropdown.content;
            if (fn.tagify.suggestedListItems.length > 1) {
                // addAllSuggestionsElm = fn.getAddAllSuggestionsElm()
                // FIXME: Fix the add all feature
                dropdownContentElm.insertBefore(fn.getAddAllSuggestionsElm(), dropdownContentElm.firstChild)
            }
        }
        
        this.onInputIcons = (e) => {
            console.log('onInput', e)
            let value = e.detail.value;
            this.tagify.settings.whitelist.length = 0; // reset the whitelist
            
            // https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort
            controller && controller.abort();
            controller = new AbortController();
            
            // show loading animation and hide the suggestions dropdown
            this.tagify.loading(true).dropdown.hide.call(this.tagify)
            wscb.send({
                cmd: 'icon_insta',
                icon: value
            }, function (_e) {
                console.log(`WS Typing Event ${value}`, 'controller', controller, _e)
                fn.tagify.settings.whitelist.splice(0, tag_wlst.length, ..._e.icons)
                fn.tagify.loading(false).dropdown.show.call(fn.tagify, value); // render the suggestions dropdown
            })
        }
        
        this.onInput = function (e) {
            this.tagify = fn.tagify
            console.log('this.tagify', this.tagify)
            let value = e.detail.value;
            this.tagify.settings.whitelist.length = 0; // reset the whitelist
            
            // https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort
            controller && controller.abort();
            controller = new AbortController();
            
            // show loading animation and hide the suggestions dropdown
            this.tagify.loading(true).dropdown.hide.call(this.tagify)
            wscb.send({
                cmd: 'icon_insta',
                icon: value
            }, (_e) => {
                console.log(`WS Typing Event ${value}`, 'controller', controller, _e)
                fn.tagify.settings.whitelist.splice(0, tag_wlst.length, ..._e.icons)
                fn.tagify.loading(false).dropdown.show.call(fn.tagify, value); // render the suggestions dropdown
            })
            /*this.tagify.settings.whitelist.splice(0, tag_wlst.length, ...e.icons)
            this.tagify.loading(false).dropdown.show.call(this.tagify, value); // render the suggestions dropdown*/
        }
        
        const tagifyDefaults = {
            tagTextProp: 'name', // very important since a custom template is used with this property as text. allows typing a "value" or a "name" to match input with whitelist
            enforceWhitelist: false,
            skipInvalid: false, // do not temporarily add invalid tags
            delimiters: ",| ;",
            dropdown: {
                closeOnSelect: !tagLimit,
                enabled: 0,
                classname: 'users-list',
                searchKeys: ['slug'] // very important to set by which keys to search for suggesttions when typing
            },
            templates: {
                tag: this.tagIconTemplate,
                dropdownItem: loadIcons ? this.suggestIcon : this.suggestTag,
                dropdownItemNoMatch: function (data) {
                    fn.transformTag(data)
                }
            },
            editTags: {
                clicks: 1,              // single click to edit a tag
                keepInvalid: true      // if after editing, tag is invalid, auto-revert
            }
            //whitelist: departments
        }
        // initialize Tagify on the above input node reference
        this.tagify = new Tagify(inputEl, {
            ...tagifyDefaults,
            ...tagifyOpts
        })
        this.tagify.on('dropdown:show dropdown:updated', this.onDropdownShow);
        this.tagify.on('dropdown:select', this.onSelectSuggestion);
        this.tagify.on('add', this.addTag)
        this.tagify.on('input', loadIcons ? this.onInput : this.onInputIcons)
    }
    return {init};
}


// Open the full screen search box
function openSearch() {
    document.getElementById("myOverlay").style.display = "block";
}

// Close the full screen search box
function closeSearch() {
    document.getElementById("myOverlay").style.display = "none";
}


(function ($) {
    $('.closebtn, .close-icon').click(function (e) {
        closeSearch()
    })
})(window.jQuery)



