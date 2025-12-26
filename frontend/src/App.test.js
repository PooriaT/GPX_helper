import { render, screen } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  it('renders the hero headline', () => {
    render(App);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Make GPX + video sync simple.');
  });
});
