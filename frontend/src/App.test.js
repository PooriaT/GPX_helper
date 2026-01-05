import { render, screen } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  it('renders the hero headline and key actions', () => {
    render(App);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('GPX Helper');
    expect(
      screen.getByRole('heading', { level: 2, name: /Trim GPX by time window/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Start time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/End time/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim track/i })).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { level: 2, name: /Render map animation/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Duration \(seconds\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution width/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution height/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();

    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(2);
    expect(screen.getByLabelText(/Optional video file/i)).toBeInTheDocument();
  });
});
