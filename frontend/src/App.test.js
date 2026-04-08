import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  afterEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('renders the trim page by default with header navigation', () => {
    render(App);

    const mainMenu = screen.getByRole('navigation', { name: /Main menu/i });

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Trim GPX');
    expect(within(mainMenu).getByRole('link', { name: /^Trim GPX$/i })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(within(mainMenu).getByRole('link', { name: /^Route animation$/i })).toBeInTheDocument();
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
    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(2);
    expect(screen.getByLabelText(/Optional video file/i)).toBeInTheDocument();
  });

  it('renders the route animation page from the hash route', async () => {
    window.location.hash = '#/animation';
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Route animation');
    });
    expect(
      within(screen.getByRole('navigation', { name: /Main menu/i })).getByRole('link', {
        name: /^Route animation$/i
      })
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('heading', { level: 2, name: /Render map animation/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Duration \(seconds\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Frames per second/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution width/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution height/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tile style/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 2, name: /Trim GPX by time window/i })).not.toBeInTheDocument();
  });

  it('shows the selected marker color in the route animation style controls', async () => {
    window.location.hash = '#/animation';
    render(App);

    await waitFor(() => {
      expect(screen.getByLabelText(/Marker color/i)).toBeInTheDocument();
    });
    const markerColorInput = screen.getByLabelText(/Marker color/i);

    await fireEvent.input(markerColorInput, { target: { value: '#ff0000' } });

    expect(screen.getByText('#ff0000')).toBeInTheDocument();
    expect(markerColorInput).toHaveValue('#ff0000');
  });
});
