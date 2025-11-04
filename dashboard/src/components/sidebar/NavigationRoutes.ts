export interface INavigationRoute {
  name: string
  displayName: string
  meta: { icon: string }
  children?: INavigationRoute[]
}
export default {
  root: {
    name: '/',
    displayName: 'navigationRoutes.home',
  },
  routes: [
    {
      name: 'home',
      displayName: 'Home',
      meta: {
        icon: 'mso-home',
      },
    },
    {
      name: 'user-vni',
      displayName: 'Mi VNI',
      meta: {
        icon: 'mso-computer',
      },
    },
  ] as INavigationRoute[],
}