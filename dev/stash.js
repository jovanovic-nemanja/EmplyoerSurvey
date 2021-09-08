$('.clockpicker').clockpicker({
donetext: 'Done',
}).find('input').change(function () {
console.log(this.value);
});

$('#start-date').clockpicker({
placement: 'bottom',
align: 'left',
autoclose: true,
'default': 'now'
});
