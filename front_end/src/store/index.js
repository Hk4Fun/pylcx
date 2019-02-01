import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    token: '',
    username: '',
    id: ''
  },
  mutations: {
    store_info (state, info) {
      state.token = info.token
      state.username = info.username
      state.id = info.id
    },
    delete_info (state) {
      state.token = ''
      state.username = ''
      state.id = ''
    }
  }
})
