import logo from './logo.svg';
import './App.css';

import ReactPlayer from 'react-player'

function App() {
    let videoPlayer;
    const videoUrl = 'https://www.youtube.com/watch?v=ysz5S6PUM-U';
    if(videoUrl){
        videoPlayer = <ReactPlayer url={videoUrl} />;
    }
  return (
    <div className="App">

        {/*<DubbingForm></DubbingForm>*/}
        {videoPlayer}
    </div>
  );
}

export default App;
