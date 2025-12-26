import { render, screen } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  it('renders the hero headline and key actions', () => {
    render(App);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Run the GPX Helper API from the browser.'
    );
    expect(screen.getByLabelText(/API base URL/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim track/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim with video/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();
  });
});
