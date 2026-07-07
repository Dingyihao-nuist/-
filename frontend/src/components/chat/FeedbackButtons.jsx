import { Button } from 'antd';
import { LikeOutlined, DislikeOutlined } from '@ant-design/icons';

export default function FeedbackButtons({ messageId, currentFeedback, onFeedback }) {
  return (
    <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
      <Button
        size="small"
        type={currentFeedback === true ? 'primary' : 'text'}
        icon={<LikeOutlined />}
        onClick={() => onFeedback(messageId, true)}
        style={{ borderRadius: 4 }}
      />
      <Button
        size="small"
        type={currentFeedback === false ? 'primary' : 'text'}
        danger={currentFeedback === false}
        icon={<DislikeOutlined />}
        onClick={() => onFeedback(messageId, false)}
        style={{ borderRadius: 4 }}
      />
    </div>
  );
}
