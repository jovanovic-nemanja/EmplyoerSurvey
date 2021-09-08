/* Echarts */
// let hiyer_donut = echarts.init(document.getElementById('hiyer-score-donut'));
// const option = {
//     tooltip: {
//         trigger: 'item'
//     },
//     legend: {
//         top: '80%',
//         left: 'center'
//     },
//     series: [
//         {
//             name: 'Hiyer Scores',
//             type: 'pie',
//             radius: ['50%', '70%'],
//             center: ['50%', '40%'],
//             avoidLabelOverlap: false,
//             labelLine: {
//                 show: false
//             },
//             label: {
//                 show: false,
//                 position: 'center'
//             },
//             emphasis: {
//                 label: {
//                     show: true,
//                     fontSize: '20',
//                     fontWeight: 'bold'
//                 }
//             },
//             labelLine: {
//                 show: false
//             },
//             itemStyle: {
//                 borderRadius: 0,
//                 borderColor: '#fff',
//                 borderWidth: 7
//             },
//             data: [
//                 {
//                     value: 32,
//                     name: 'PERFORMANCE',
//                     itemStyle: {
//                         color: '#FF5B61'
//                     }
//                 },
//                 {
//                     value: 9,
//                     name: 'PEER',
//                     itemStyle: {
//                         color: '#6665DD'
//                     }
//                 },
//                 {
//                     value: 10,
//                     name: 'MANAGED UP',
//                     itemStyle: {
//                         color: '#29E7CD'
//                     }
//                 },
//                 {
//                     value: 49,
//                     name: 'CQI',
//                     // selected: false,
//                     // label: {
//                     //     show: false,
//                     //     fontSize: '49',
//                     //     position: 'center',
//                     //     fontWeight: 'bold',
//                     //     color: '#FF5BC3',
//                     //     verticalAlign: 'middle'
//                     // },
//                     // emphasis: {
//                     //     label: {
//                     //         show: true,
//                     //         color: '#FF5BC3',
//                     //         fontSize: '35',
//                     //         fontWeight: 'bold',
//                     //         position: 'center',
//                     //         verticalAlign: 'middle'
//                     //     }
//                     // },
//                     itemStyle: {
//                         color: '#FF5BC3'
//                     }
//                 },
//             ]
//         }
//     ]
// };
// hiyer_donut.setOption(option);

let tag_donut_1 = echarts.init(document.getElementById('tag-donut-1'));
const tag_donut_1_options = {
    series: [
        {
            name: 'Hiyer Scores',
            type: 'pie',
            radius: ['55%', '80%'],
            avoidLabelOverlap: false,
            labelLine: {
                show: false
            },
            itemStyle: {
                borderRadius: 0,
                borderColor: '#fff',
                borderWidth: 7,
                color: '#FF5B61'
            },
            label: {
                show: true,
                fontSize: '35',
                position: 'center',
                fontWeight: 'bold',
                color: '#FF5B61',
                verticalAlign: 'middle'
            },
            emphasis: {
                label: {
                    show: true,
                    color: '#FF5B61',
                    fontSize: '35',
                    fontWeight: 'bold',
                }
            },
            data: [
                {
                    value: responseRate['performance'] || 0,
                    name: (responseRate['performance'] || 0) + '%',
                    selected: true,
                },
                (responseRate['performance'] || 0) >= 100 ? null : {
                    value: 100 - (responseRate['performance'] || 0),
                    name: '',
                    label: {
                        show: false,
                        color: '#FFFFFF'
                    },
                    itemStyle: {
                        show: false,
                        color: '#FFFFFF'
                    }
                }
            ]
        }
    ]
};
tag_donut_1.setOption(tag_donut_1_options);

let tag_donut_2 = echarts.init(document.getElementById('tag-donut-2'));
const tag_donut_2_options = {
    series: [
        {
            name: 'Hiyer Scores',
            type: 'pie',
            radius: ['55%', '80%'],
            avoidLabelOverlap: false,
            labelLine: {
                show: false
            },
            itemStyle: {
                borderRadius: 0,
                borderColor: '#fff',
                borderWidth: 7,
                color: '#6665DD'
            },
            label: {
                show: true,
                fontSize: '35',
                position: 'center',
                fontWeight: 'bold',
                color: '#6665DD',
                verticalAlign: 'middle'
            },
            emphasis: {
                label: {
                    show: true,
                    color: '#6665DD',
                    fontSize: '35',
                    fontWeight: 'bold',
                }
            },
            data: [
                {
                    value: (responseRate['peer-review'] || 0),
                    name: (responseRate['peer-review'] || 0) + '%',
                    selected: false,
                },
                (responseRate['peer-review'] || 0) >= 100 ? null : {
                    value: 100 - (responseRate['peer-review'] || 0),
                    name: '',
                    label: {
                        show: false,
                        color: '#FFFFFF'
                    },
                    itemStyle: {
                        show: false,
                        color: '#FFFFFF'
                    }
                }
            ]
        }
    ]
};
tag_donut_2.setOption(tag_donut_2_options);


let tag_donut_3 = echarts.init(document.getElementById('tag-donut-3'));
const tag_donut_3_options = {
    series: [
        {
            name: 'Hiyer Scores',
            type: 'pie',
            radius: ['55%', '80%'],
            avoidLabelOverlap: false,
            labelLine: {
                show: false
            },
            itemStyle: {
                borderRadius: 0,
                borderColor: '#fff',
                borderWidth: 7,
                color: '#29E7CD'
            },
            label: {
                show: true,
                fontSize: '35',
                position: 'center',
                fontWeight: 'bold',
                color: '#29E7CD',
                verticalAlign: 'middle'
            },
            emphasis: {
                label: {
                    show: true,
                    color: '#29E7CD',
                    fontSize: '35',
                    fontWeight: 'bold',
                }
            },
            data: [
                {
                    value: (responseRate['managed-up'] || 0),
                    name: (responseRate['managed-up'] || 0) + '%',
                    selected: false,
                },
                (responseRate['managed-up'] || 0) >= 100 ? null : {
                    value: 100 - (responseRate['managed-up'] || 0),
                    name: '',
                    label: {
                        show: false,
                        color: '#FFFFFF'
                    },
                    itemStyle: {
                        show: false,
                        color: '#FFFFFF'
                    }
                }
            ]
        }
    ]
};
tag_donut_3.setOption(tag_donut_3_options);

let tag_donut_4 = echarts.init(document.getElementById('tag-donut-4'));
const tag_donut_4_options = {
    series: [
        {
            name: 'Hiyer Scores',
            type: 'pie',
            radius: ['55%', '80%'],
            avoidLabelOverlap: false,
            labelLine: {
                show: false
            },
            itemStyle: {
                borderRadius: 0,
                borderColor: '#fff',
                borderWidth: 7,
                color: '#FF5BC3'
            },
            label: {
                show: true,
                fontSize: '35',
                position: 'center',
                fontWeight: 'bold',
                color: '#FF5BC3',
                verticalAlign: 'middle'
            },
            emphasis: {
                label: {
                    show: true,
                    color: '#FF5BC3',
                    fontSize: '35',
                    fontWeight: 'bold',
                }
            },
            data: [
                {
                    value: (responseRate['cqi'] || 0),
                    name: (responseRate['cqi'] || 0) + '%',
                    selected: false,
                },
                (responseRate['cqi'] || 0) >= 100 ? null : {
                    value: 100 - (responseRate['cqi'] || 0),
                    name: '',
                    label: {
                        show: false,
                        color: '#FFFFFF'
                    },
                    itemStyle: {
                        show: false,
                        color: '#FFFFFF'
                    }
                }
            ]
        }
    ]
};
tag_donut_4.setOption(tag_donut_4_options);


let response_rot = new Chartist.Line('.response_rot', {
    labels: ['3/01', '3/10', '3/20', '3/31'],
    series: [
        [80, 40, 55, 90],
        [30, 20, 5, 60],
        // [50, 40, 30, 20, 50, 85]
    ]
}, {
    low: 0,
    showArea: false,
    showPoint: true,
    fullWidth: true,
    areaBase: 0,
    height: '300px',
    axisX: {
        areaBase: 0,
        showArea: false,
        showLabel: false
    },
    axisY: {
        showLabel: false,
        showGrid: false,
        areaBase: 0,
        showArea: false
    }
});
response_rot.on('draw', function (data) {
    if (data.type === 'line' || data.type === 'area') {
        data.element.animate({
            d: {
                begin: 2000 * data.index,
                dur: 2000,
                from: data.path.clone().scale(1, 0).translate(0, data.chartRect.height()).stringify(),
                to: data.path.clone().stringify(),
                easing: Chartist.Svg.Easing.easeOutQuint
            }
        });
    }
});
