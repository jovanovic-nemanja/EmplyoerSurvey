


(function ($) {
    "use strict"
    
    var UroraApp = (function () {
        
        "use strict"
        
        var windowRef = $(window)
        var bodyRef = $('body')
        var docRef = $(document)
        var bodyContent = $('.body-content')
        var contentWrapper = $("#wrapper")
        var notificationPanel = $(".slimscroll-noti")
        var preloaderStatus = $('#status')
        var preloaderContainer = $('#preloader')
        var mobileToggle = $('#mobileToggle')
        var fullScreenToggle = $("#btn-fullscreen")
        var menuItems = $(".navigation-menu>li")
        var menuSubItems = $(".navigation-menu li.has-submenu a[href='#']")
        var navigationMenuItems = $(".navigation-menu a")
        
        //inits widgets
        var initWidgets = function () {
            //tooltip
            $('[data-toggle="tooltip"]').tooltip()
            //popover
            $('[data-toggle="popover"]').popover()
        }
        
        //load topbar
        var initTopbar = function () {
            var t = this;
            //scroll
            notificationPanel.slimscroll({
                height: '230px',
                position: 'right',
                size: "5px",
                color: '#98a6ad',
                wheelStep: 10
            })
            
            // topbar menu toggle for mobile/smaller devices
            mobileToggle.on('click', function (e) {
                $(this).toggleClass('open')
                $('#navigation').slideToggle(400)
                return false
            })
            
            // menu items
            menuItems.slice(-1).addClass('last-elements')
            
            menuSubItems.on('click', function (e) {
                if ($(window).width() < 992) {
                    e.preventDefault()
                    $(this).parent('li').toggleClass('open').find('.submenu:first').toggleClass('open')
                }
            })
            
            //activate menu item by url
            navigationMenuItems.each(function () {
                if (this.href == window.location.href) {
                    $(this).parent().addClass("active") // add active to li of the current link
                    $(this).parent().parent().parent().addClass("active") // add active class to an anchor
                    $(this).parent().parent().parent().parent().parent().addClass("active") // add active class to an anchor
                }
            })
        }
        
        //toggle full screen
        var toggleFullscreen = function (e) {
            fullScreenToggle.on("click", function (e) {
                e.preventDefault()
                if (!document.fullscreenElement && /* alternative standard method */ !document.mozFullScreenElement && !document.webkitFullscreenElement) {  // current working methods
                    if (document.documentElement.requestFullscreen) {
                        document.documentElement.requestFullscreen()
                    } else if (document.documentElement.mozRequestFullScreen) {
                        document.documentElement.mozRequestFullScreen()
                    } else if (document.documentElement.webkitRequestFullscreen) {
                        document.documentElement.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT)
                    }
                } else {
                    if (document.cancelFullScreen) {
                        document.cancelFullScreen()
                    } else if (document.mozCancelFullScreen) {
                        document.mozCancelFullScreen()
                    } else if (document.webkitCancelFullScreen) {
                        document.webkitCancelFullScreen()
                    }
                }
                return false
            })
        }
        
        //on window load call back function
        var onWinLoad = function (e) {
            preloaderStatus.fadeOut()
            preloaderContainer.delay(350).fadeOut('slow')
            // bodyRef.delay(350).css({
            //     'overflow': 'visible'
            // })
        }
        
        //on document ready callback function
        var onDocReady = function (e) {
            // apply material design
            bodyRef.bootstrapMaterialDesign()
            
            //widgets
            initWidgets()
            
            // load topbar
            initTopbar()
            
            // full screen
            toggleFullscreen()
        }
        
        //binds the events to required elements
        var bindEvents = function () {
            docRef.ready(onDocReady)
            windowRef.on('load', onWinLoad)
        }
        
        // init - initilizes various widgets, elements, events, etc
        var init = function () {
            bindEvents()
        }
        
        return {
            init: init
        }
    }())
    
    UroraApp.init()
}(window.jQuery))
