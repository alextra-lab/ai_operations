import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import {
  SanitizePipe,
  SanitizeTextPipe,
  SanitizeUrlPipe,
} from '../pipes/sanitize.pipe';
import { SecurityHeadersService } from './security-headers.service';
import { SecurityMonitoringService } from './security-monitoring.service';
import { XSSProtectionService } from './xss-protection.service';

/**
 * Security module that provides comprehensive security services and pipes.
 * This module should be imported by the main app module to enable security features.
 */
@NgModule({
  declarations: [SanitizePipe, SanitizeTextPipe, SanitizeUrlPipe],
  imports: [CommonModule],
  providers: [
    SecurityHeadersService,
    XSSProtectionService,
    SecurityMonitoringService,
  ],
  exports: [SanitizePipe, SanitizeTextPipe, SanitizeUrlPipe],
})
export class SecurityModule {}
