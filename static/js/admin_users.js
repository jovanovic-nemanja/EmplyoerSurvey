let user_table


const access_levels = {
    1: 'Employee',
    8: 'Superuser',
    9: 'Admin'
}


const is_el = element => {
    return element instanceof Element || element instanceof HTMLDocument
}

console.log('here1')
const format_phone = (phone_number) => {
    if (phone_number != null) {
        let phone = phone_number.toString().replace(/\D/g, '')
        const match = phone.match(/^(\d{1,3})(\d{0,3})(\d{0,4})$/)
        if (match) {
            phone = `${match[1]}${match[2] ? ' ' : ''}${match[2]}${match[3] ? '-' : ''}${match[3]}`
        }
        return phone
    } else {
        return 'None'
    }
}

(function ($) {
    $(() => {
        console.log('here')
        user_table = $('#users_table').DataTable({
            ajax: {
                url: "/api/admin/list_users",
                contentType: 'application/json',
                type: "GET",
                crossDomain: true,
                dataType: 'json',
                dataSrc: '',
            },
            //serverSide: true,
            //dataSrc: "",
            //dataType: 'json',
            //"processing": true,
            /*rowReorder: {
                selector: 'td:nth-child(2)'
            },
            responsive: {
                details: {
                    //display: $.fn.dataTable.Responsive.display.childRowImmediate,
                    type: 'column',
                    target: 'tr'
                }
            },*/
            responsive: {
                details: {
                    //display: $.fn.dataTable.Responsive.display.childRowImmediate,
                    type: 'column',
                    target: 'tr'
                }
            },
            columns: [
                {
                    name: 'gravatar',
                    title: '',
                    //targets: [0],
                    data: 'gravatar',
                    //defaultContent: '',
                    'render': function (data, type, row, meta) {
                        console.log('grav', data)
                        return `<img src="https://robohash.org/${data}?gravatar=hashed" height="40" />`;
                    }
                },
                {
                    name: 'who', title: 'Who', data: 'first_name',
                    render: (data, type, row) => {
                        console.log(data)
                        return data != null ? `${data} ${row.last_name.charAt(0).toUpperCase()}.` : 'None'
                    }
                },
                {
                    name: 'user_group', title: 'Group', data: 'user_level',
                    render: data => {
                        return access_levels[data]
                    }
                },
                {name: 'email_address', title: 'Email', data: 'email_address', defaultContent: 'None'},
                // {name: 'date_created', title: 'Joined', data: 'date_registered'},
                // {name: 'last_active', title: 'Seen', data: 'last_login_date', defaultContent: 'Never'},
                /*{
                    name: 'mobile_number',
                    title: 'Phone',
                    data: 'mobile_number',
                    defaultContent: 'None',
                    render: format_phone
                },*/
                {
                    name: 'actions',
                    title: '',
                    className: "text-center",
                    render: (data, type, row, meta) => {
                        if (!row.checked) {
                            console.log('row not checked')
                        }
                        return `<a href="#"><i class="fa fa-times fa-lg"></i></a>
                                        &nbsp;
                                        <a href="#"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512" fill="#727272" width="16"><path d="M4.69 439.43c-6.25 6.25-6.25 16.38 0 22.63l45.26 45.25c6.25 6.25 16.38 6.25 22.63 0l235.87-235.87-67.88-67.88L4.69 439.43zM525.74 160l-52.93-52.93 34.5-34.5c6.25-6.25 6.25-16.38 0-22.63L462.06 4.69c-6.25-6.25-16.38-6.25-22.63 0l-34.5 34.5-29.81-29.82C368.87 3.12 360.68 0 352.49 0s-16.38 3.12-22.63 9.37l-96.49 96.49c-12.5 12.5-12.5 32.76 0 45.25L384 301.74V416h32c123.71 0 224-100.29 224-224v-32H525.74zM448 348.79v-37.94c39.28-16.25 70.6-47.56 86.84-86.84h37.94C560.03 286.6 510.6 336.03 448 348.79z"/></svg></a>
                                        `
                    }
                }
                //{ name: 'id', title: 'id', data: 'id' },
            ],
            //asStripeClasses: [],
            //scrollY: '100vh',
            // autoWidth: false,
            // deferRender: true,
            //scrollCollapse: false,
            scroller: {
                loadingIndicator: true
            },
            language: {
                search: "",
                searchPlaceholder: "Search"
            },
            initComplete: () => {
                console.log('INIT START')
                /*$('.dataTables_filter input').addClass('form-control form-control-lg')
                $('#container').css('display', 'block')
                //this.fnAdjustColumnSizing()
                $($.fn.dataTable.tables(true)).DataTable()
                    .columns.adjust()
                    .responsive.recalc()
                    .fixedColumns().relayout().draw()

                $(".dataTables_scrollHeadInner").css({"width": "111%"});
                $(".table ").css({"width": "100%"});
                //this.fnDraw()
                //this.tables.columns.adjust().draw()

                 */
            },
            info: false,
            scrollCollapse: false,
            scrollY: '100vh',
            deferRender: true,
            /*asStripeClasses: [],
            scrollY:        '100vh',
            deferRender:    true,
            scrollCollapse: false,
            scroller:       {
                loadingIndicator: true
            },
            info: false*/
        })
        //update_table('users_table', dataSet)
    })
    setInterval(function () {
        $(".dataTables_scrollHeadInner").css({"width": "125%"});
        $(".dataTable td").css({"padding": "32px"});
        // $(".table").css({"width": "125%"});
        // $("tbody").css({"width": "125%"});
        // $("tr").css({"width": "125%"});
    }, 500)
})(jQuery)
