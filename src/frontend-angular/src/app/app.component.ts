import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SecurityInitializationService } from './core/security/security-initialization.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit {
  readonly title = 'AI Operations Platform';
  private securityInit = inject(SecurityInitializationService);

  ngOnInit(): void {
    // Initialize security features on app startup
    this.securityInit.initializeSecurity();
  }
}
