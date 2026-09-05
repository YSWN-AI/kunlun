import{ab as a,az as d,ad as e,an as o,ac as l,d as u,h as f,a7 as g,aJ as b,av as h,ak as m,bw as $,o as w,c as x,a as v}from"./index-wHqlCVHi.js";const t="0!important",p="-1px!important";function n(r){return o(`${r}-type`,[e("& +",[a("button",{},[o(`${r}-type`,[l("border",{borderLeftWidth:t}),l("state-border",{left:p})])])])])}function i(r){return o(`${r}-type`,[e("& +",[a("button",[o(`${r}-type`,[l("border",{borderTopWidth:t}),l("state-border",{top:p})])])])])}const B=a("button-group",`
 flex-wrap: nowrap;
 display: inline-flex;
 position: relative;
`,[d("vertical",{flexDirection:"row"},[d("rtl",[a("button",[e("&:first-child:not(:last-child)",`
 margin-right: ${t};
 border-top-right-radius: ${t};
 border-bottom-right-radius: ${t};
 `),e("&:last-child:not(:first-child)",`
 margin-left: ${t};
 border-top-left-radius: ${t};
 border-bottom-left-radius: ${t};
 `),e("&:not(:first-child):not(:last-child)",`
 margin-left: ${t};
 margin-right: ${t};
 border-radius: ${t};
 `),n("default"),o("ghost",[n("primary"),n("info"),n("success"),n("warning"),n("error")])])])]),o("vertical",{flexDirection:"column"},[a("button",[e("&:first-child:not(:last-child)",`
 margin-bottom: ${t};
 margin-left: ${t};
 margin-right: ${t};
 border-bottom-left-radius: ${t};
 border-bottom-right-radius: ${t};
 `),e("&:last-child:not(:first-child)",`
 margin-top: ${t};
 margin-left: ${t};
 margin-right: ${t};
 border-top-left-radius: ${t};
 border-top-right-radius: ${t};
 `),e("&:not(:first-child):not(:last-child)",`
 margin: ${t};
 border-radius: ${t};
 `),i("default"),o("ghost",[i("primary"),i("info"),i("success"),i("warning"),i("error")])])])]),y={size:String,vertical:Boolean},k=u({name:"ButtonGroup",props:y,setup(r){const{mergedClsPrefixRef:s,mergedRtlRef:c}=g(r);return b("-button-group",B,s),m($,r),{rtlEnabled:h("ButtonGroup",c,s),mergedClsPrefix:s}},render(){const{mergedClsPrefix:r}=this;return f("div",{class:[`${r}-button-group`,this.rtlEnabled&&`${r}-button-group--rtl`,this.vertical&&`${r}-button-group--vertical`],role:"group"},this.$slots)}}),S={xmlns:"http://www.w3.org/2000/svg","xmlns:xlink":"http://www.w3.org/1999/xlink",viewBox:"0 0 1024 1024"},C=v("path",{d:"M858.5 763.6a374 374 0 0 0-80.6-119.5a375.63 375.63 0 0 0-119.5-80.6c-.4-.2-.8-.3-1.2-.5C719.5 518 760 444.7 760 362c0-137-111-248-248-248S264 225 264 362c0 82.7 40.5 156 102.8 201.1c-.4.2-.8.3-1.2.5c-44.8 18.9-85 46-119.5 80.6a375.63 375.63 0 0 0-80.6 119.5A371.7 371.7 0 0 0 136 901.8a8 8 0 0 0 8 8.2h60c4.4 0 7.9-3.5 8-7.8c2-77.2 33-149.5 87.8-204.3c56.7-56.7 132-87.9 212.2-87.9s155.5 31.2 212.2 87.9C779 752.7 810 825 812 902.2c.1 4.4 3.6 7.8 8 7.8h60a8 8 0 0 0 8-8.2c-1-47.8-10.9-94.3-29.5-138.2zM512 534c-45.9 0-89.1-17.9-121.6-50.4S340 407.9 340 362c0-45.9 17.9-89.1 50.4-121.6S466.1 190 512 190s89.1 17.9 121.6 50.4S684 316.1 684 362c0 45.9-17.9 89.1-50.4 121.6S557.9 534 512 534z",fill:"currentColor"},null,-1),_=[C],z=u({name:"UserOutlined",render:function(s,c){return w(),x("svg",S,_)}});export{k as N,z as U};
