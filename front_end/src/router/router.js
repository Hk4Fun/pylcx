import Vue from 'vue'
import Router from 'vue-router'
import Login from '../pages/login/Login'
import Admin from '../pages/admin/Admin'
import User from '../pages/user/User'

Vue.use(Router)

export default new Router({
  routes: [{
    path: '/login',
    name: 'login',
    component: Login
  }, {
    path: '/admin',
    name: 'admin',
    component: Admin
  }, {
    path: '/user',
    name: 'user',
    component: User
  }, {
    path: '*',
    redirect: '/login'
  }]
})
