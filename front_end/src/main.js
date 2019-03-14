import Vue from 'vue'
import App from './App.vue'
import ElementUI from 'element-ui'
import axios from 'axios'
import VueAxios from 'vue-axios'
import VueNativeSock from 'vue-native-websocket'
import router from './router/router'
import store from './store'
import VeLine from 'v-charts/lib/line.common'
import VePie from 'v-charts/lib/pie.common'
import 'element-ui/lib/theme-chalk/index.css'
import 'animate.css'

Vue.config.productionTip = false;
Vue.use(ElementUI);
Vue.use(VueAxios, axios);
Vue.use(VueNativeSock, 'ws://59.110.238.88:8000/online_users');
Vue.component(VeLine.name, VeLine);
Vue.component(VePie.name, VePie);

axios.defaults.timeout = 5000;
axios.defaults.baseURL ='http://59.110.238.88:8000';

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
