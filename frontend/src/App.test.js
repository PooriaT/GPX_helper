import { fireEvent, render, screen } from '@testing-library/svelte';
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
      screen.getByRole('heading', { level: 2, name: /Split GPX by multiple videos/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^Video files$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create ZIP/i })).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { level: 2, name: /Render map animation/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Duration \(seconds\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Frames per second/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution width/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution height/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tile style/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();

    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(3);
    expect(screen.getByLabelText(/Optional video file/i)).toBeInTheDocument();
  });

  it('shows the selected marker color in the route animation style controls', async () => {
    render(App);

    const markerColorInput = screen.getByLabelText(/Marker color/i);

    await fireEvent.input(markerColorInput, { target: { value: '#ff0000' } });

    expect(screen.getByText('#ff0000')).toBeInTheDocument();
    expect(markerColorInput).toHaveValue('#ff0000');
  });
});
