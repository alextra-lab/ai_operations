import { HttpContextToken } from '@angular/common/http';

export const BYPASS_AUTH_INTERCEPTOR = new HttpContextToken<boolean>(
  () => false
);

export const BYPASS_SECURITY_INTERCEPTOR = new HttpContextToken<boolean>(
  () => false
);
