import { render, screen } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  it('renders the hero headline and key actions', () => {
    render(App);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Run the GPX Helper API from the browser.'
    );
    expect(
      screen.getByRole('heading', { level: 2, name: /Trim GPX by time window/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Start time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/End time/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim track/i })).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { level: 2, name: /Trim GPX using video/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^Video file$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim with video/i })).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { level: 2, name: /Render map animation/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Duration \(seconds\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();

    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(3);
    expect(screen.getByLabelText(/Optional video file/i)).toBeInTheDocument();
  });
});
