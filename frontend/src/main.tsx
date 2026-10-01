import { createRoot } from 'react-dom/client'
import { AuthProvider } from 'react-oidc-context'
import App from './App'

const cognitoAuthConfig = {  
  authority: "https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_QkRoNc1Ea",
  client_id: "or6n2iielpk6febma3fve0kbs",
  redirect_uri: window.location.origin,
  response_type: "code",
  scope: "openid email",
  onSigninCallback: () => window.history.replaceState({}, document.title, window.location.pathname),
};
createRoot(document.getElementById('root')!).render(
   <AuthProvider {...cognitoAuthConfig}>
    <App />
  </AuthProvider>
)
